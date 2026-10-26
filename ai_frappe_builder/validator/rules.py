"""
rules.py — Deterministic Frappe schema validation rules.
"""

from __future__ import annotations

import ast
import re

from ai_frappe_builder.models.app_spec_v2 import (
    DocTypeSpec,
    WorkflowSpec,
)
from ai_frappe_builder.models.validation import FixHint, ValidationReport
from ai_frappe_builder.validator.catalog import (
    get_fieldtypes_catalog,
    get_reserved_fieldnames,
)

NAMING_SERIES_REGEX = re.compile(r"^[A-Z0-9\-_]+(-\..*)?-\.(#+|##+|###+|####+|#####+)$")
DOCTYPE_NAME_REGEX = re.compile(r"^[A-Z][a-zA-Z0-9]*(\s[A-Z0-9][a-zA-Z0-9]*)*$")
FIELDNAME_REGEX = re.compile(r"^[a-z][a-z0-9_]*$")
MAX_FIELDS_WARNING = 40


def validate_doctype_naming(dt: DocTypeSpec, report: ValidationReport) -> None:
    """Rule 1: Title Case names and length."""
    name = dt.name.strip()
    if len(name) < 2 or len(name) > 60:
        report.add_error(
            rule="doctype_name_length",
            message=f"DocType name '{name}' length ({len(name)}) must be between 2 and 60 characters.",
            doctype=name,
        )

    if not DOCTYPE_NAME_REGEX.match(name):
        suggested = " ".join(word.capitalize() for word in name.split())
        report.add_error(
            rule="doctype_name_title_case",
            message=f"DocType name '{name}' is not idiomatic Title Case.",
            doctype=name,
            fix_hint=FixHint(
                rule="doctype_name_title_case",
                doctype=name,
                message=f"Rename DocType to '{suggested}'.",
                suggested_patch={
                    "op": "replace",
                    "path": "/app/doctypes/[index]/name",
                    "value": suggested,
                },
            ),
        )


def validate_fieldnames(dt: DocTypeSpec, report: ValidationReport) -> None:
    """Rule 2: Reserved names, uniqueness, lowercase snake_case, length."""
    reserved = get_reserved_fieldnames()
    seen_fieldnames: set[str] = set()

    for idx, field in enumerate(dt.fields):
        fname = field.fieldname.strip()
        flabel = field.label.strip()

        # Check reserved
        if fname in reserved:
            suggested = f"custom_{fname}"
            report.add_error(
                rule="reserved_fieldname",
                message=f"Field '{fname}' uses a reserved Frappe internal name.",
                doctype=dt.name,
                field=fname,
                fix_hint=FixHint(
                    rule="reserved_fieldname",
                    doctype=dt.name,
                    field=fname,
                    message=f"Rename field '{fname}' to '{suggested}'.",
                    suggested_patch={
                        "op": "replace",
                        "path": f"/app/doctypes/[index]/fields/{idx}/fieldname",
                        "value": suggested,
                    },
                ),
            )

        # Check unique within doctype
        if fname in seen_fieldnames:
            report.add_error(
                rule="duplicate_fieldname",
                message=f"Duplicate fieldname '{fname}' defined in DocType '{dt.name}'.",
                doctype=dt.name,
                field=fname,
            )
        seen_fieldnames.add(fname)

        # Check syntax
        is_break = field.fieldtype in {"Section Break", "Column Break", "Tab Break"}
        if not is_break and not FIELDNAME_REGEX.match(fname):
            report.add_error(
                rule="fieldname_snake_case",
                message=f"Fieldname '{fname}' must be lowercase snake_case starting with a letter.",
                doctype=dt.name,
                field=fname,
            )

        # Length constraints
        if len(fname) > 64:
            report.add_error(
                rule="fieldname_max_length",
                message=f"Fieldname '{fname}' exceeds maximum 64 characters ({len(fname)}).",
                doctype=dt.name,
                field=fname,
            )
        if len(flabel) > 140:
            report.add_error(
                rule="label_max_length",
                message=f"Field label '{flabel}' exceeds maximum 140 characters.",
                doctype=dt.name,
                field=fname,
            )


def validate_fieldtypes_and_options(
    dt: DocTypeSpec,
    all_known_doctypes: set[str],
    child_doctype_names: set[str],
    report: ValidationReport,
) -> None:
    """Rule 3, 4, 12 & Fieldtypes Matrix: Types and options validation."""
    catalog = get_fieldtypes_catalog()
    doc_fieldnames = {f.fieldname for f in dt.fields}

    for field in dt.fields:
        ftype = field.fieldtype

        if catalog and ftype not in catalog:
            report.add_error(
                rule="unknown_fieldtype",
                message=f"Field '{field.fieldname}' has invalid Frappe fieldtype '{ftype}'.",
                doctype=dt.name,
                field=field.fieldname,
            )
            continue

        opts = (field.options or "").strip()

        # Link validation
        if ftype == "Link":
            if not opts:
                report.add_error(
                    rule="link_missing_options",
                    message=f"Link field '{field.fieldname}' must specify target DocType in 'options'.",
                    doctype=dt.name,
                    field=field.fieldname,
                )
            elif opts not in all_known_doctypes:
                report.add_error(
                    rule="link_unknown_target",
                    message=f"Link field '{field.fieldname}' targets unknown DocType '{opts}'.",
                    doctype=dt.name,
                    field=field.fieldname,
                    fix_hint=FixHint(
                        rule="link_unknown_target",
                        doctype=dt.name,
                        field=field.fieldname,
                        message=f"Verify target DocType '{opts}' or create it.",
                    ),
                )

        # Table & Table MultiSelect validation
        elif ftype in ("Table", "Table MultiSelect"):
            if not opts:
                report.add_error(
                    rule="table_missing_options",
                    message=f"Table field '{field.fieldname}' must specify child DocType in 'options'.",
                    doctype=dt.name,
                    field=field.fieldname,
                )
            elif opts not in child_doctype_names:
                report.add_error(
                    rule="table_target_not_child",
                    message=(
                        f"Table field '{field.fieldname}' targets '{opts}', which is either missing "
                        f"from the spec or does not have istable=1."
                    ),
                    doctype=dt.name,
                    field=field.fieldname,
                    fix_hint=FixHint(
                        rule="table_target_not_child",
                        doctype=opts,
                        message=f"Ensure DocType '{opts}' is defined with istable: true.",
                    ),
                )

        # Dynamic Link validation
        elif ftype == "Dynamic Link":
            if not opts:
                report.add_error(
                    rule="dynamic_link_missing_options",
                    message=f"Dynamic Link field '{field.fieldname}' requires 'options' pointing to a Link field.",
                    doctype=dt.name,
                    field=field.fieldname,
                )
            elif opts not in doc_fieldnames:
                report.add_error(
                    rule="dynamic_link_invalid_pointer",
                    message=f"Dynamic Link field '{field.fieldname}' points to non-existent field '{opts}'.",
                    doctype=dt.name,
                    field=field.fieldname,
                )

        # Select validation
        elif ftype == "Select":
            if not opts:
                report.add_warning(
                    rule="select_empty_options",
                    message=f"Select field '{field.fieldname}' should have newline-separated options.",
                    doctype=dt.name,
                    field=field.fieldname,
                )


def validate_child_table_rules(
    dt: DocTypeSpec,
    referenced_child_doctypes: set[str],
    report: ValidationReport,
) -> None:
    """Rule 5 & 6: Child table flags, autoname, and permissions."""
    if dt.istable:
        if dt.permissions:
            report.add_error(
                rule="child_table_permissions",
                message=f"Child DocType '{dt.name}' (istable=1) must NOT have permission rows.",
                doctype=dt.name,
                fix_hint=FixHint(
                    rule="child_table_permissions",
                    doctype=dt.name,
                    message="Remove permission rows from child table.",
                    suggested_patch={
                        "op": "replace",
                        "path": "/app/doctypes/[index]/permissions",
                        "value": [],
                    },
                ),
            )
        if dt.autoname.strip().lower() != "hash":
            report.add_error(
                rule="child_table_autoname_hash",
                message=f"Child DocType '{dt.name}' autoname must be 'hash', got '{dt.autoname}'.",
                doctype=dt.name,
                fix_hint=FixHint(
                    rule="child_table_autoname_hash",
                    doctype=dt.name,
                    message="Set autoname to 'hash'.",
                    suggested_patch={
                        "op": "replace",
                        "path": "/app/doctypes/[index]/autoname",
                        "value": "hash",
                    },
                ),
            )
        if dt.is_submittable:
            report.add_error(
                rule="child_table_not_submittable",
                message=f"Child DocType '{dt.name}' cannot be submittable (is_submittable must be false).",
                doctype=dt.name,
            )
        # Orphan detection
        if dt.name not in referenced_child_doctypes:
            report.add_warning(
                rule="orphan_child_table",
                message=f"Child DocType '{dt.name}' is defined with istable=1 but is not referenced by any Table field.",
                doctype=dt.name,
            )
    else:
        # Non-child doctype must have autoname and permissions
        if not dt.autoname:
            report.add_error(
                rule="doctype_missing_autoname",
                message=f"DocType '{dt.name}' missing autoname scheme.",
                doctype=dt.name,
            )
        if not dt.permissions and not dt.is_single:
            report.add_error(
                rule="doctype_missing_permissions",
                message=f"DocType '{dt.name}' has no permissions rows. System Manager is required.",
                doctype=dt.name,
            )


def validate_permissions_system_manager(dt: DocTypeSpec, report: ValidationReport) -> None:
    """Rule 10: System Manager full CRUD."""
    if dt.istable or dt.is_single:
        return

    sm_rows = [p for p in dt.permissions if p.role == "System Manager"]
    if not sm_rows:
        report.add_error(
            rule="missing_system_manager_role",
            message=f"DocType '{dt.name}' must grant permissions to 'System Manager'.",
            doctype=dt.name,
        )
    else:
        sm = sm_rows[0]
        missing = [
            attr for attr in ("read", "write", "create", "delete") if not getattr(sm, attr, False)
        ]
        if missing:
            report.add_error(
                rule="incomplete_system_manager_permissions",
                message=f"DocType '{dt.name}' System Manager is missing basic permissions: {missing}.",
                doctype=dt.name,
            )


def validate_autoname_scheme(dt: DocTypeSpec, report: ValidationReport) -> None:
    """Rule 7: Autoname pattern verification."""
    if dt.istable:
        return

    auto = dt.autoname.strip()
    if auto.startswith("naming_series:"):
        opts = (dt.naming_series_options or "").strip()
        if not opts:
            report.add_warning(
                rule="naming_series_empty_options",
                message=f"DocType '{dt.name}' uses naming_series but naming_series_options is empty.",
                doctype=dt.name,
            )
        else:
            for line in opts.splitlines():
                line = line.strip()
                if line and not NAMING_SERIES_REGEX.match(line):
                    report.add_warning(
                        rule="naming_series_pattern_mismatch",
                        message=f"DocType '{dt.name}' naming_series option '{line}' does not match standard pattern.",
                        doctype=dt.name,
                    )
    elif auto.startswith("field:"):
        fname = auto.split(":", 1)[1].strip()
        matched_field = next((f for f in dt.fields if f.fieldname == fname), None)
        if not matched_field:
            report.add_error(
                rule="autoname_field_missing",
                message=f"DocType '{dt.name}' autoname specifies '{auto}' but field '{fname}' does not exist.",
                doctype=dt.name,
            )
        elif not matched_field.unique and not matched_field.reqd:
            report.add_warning(
                rule="autoname_field_not_unique",
                message=f"DocType '{dt.name}' autoname field '{fname}' should have unique=True or reqd=True.",
                doctype=dt.name,
            )
    elif auto in ("hash", "autoincrement", "Prompt"):
        pass
    elif auto.startswith("format:"):
        pass
    else:
        # Check if it matches direct naming series pattern e.g. "RENT-.YYYY.-.#####"
        if not NAMING_SERIES_REGEX.match(auto):
            report.add_warning(
                rule="unknown_autoname_pattern",
                message=f"DocType '{dt.name}' autoname '{auto}' uses non-standard scheme.",
                doctype=dt.name,
            )


def validate_layout_breaks(dt: DocTypeSpec, report: ValidationReport) -> None:
    """Layout integrity: placement of Section Break, Column Break, and Tab Break."""
    if not dt.fields:
        return

    # Check first field
    if dt.fields[0].fieldtype == "Column Break":
        report.add_error(
            rule="invalid_first_break",
            message=f"DocType '{dt.name}' starts with Column Break; must be preceded by a field or Section Break.",
            doctype=dt.name,
            field=dt.fields[0].fieldname,
        )

    last_type: str | None = None
    for field in dt.fields:
        ftype = field.fieldtype
        is_break = ftype in {"Section Break", "Column Break", "Tab Break"}

        if is_break and field.reqd:
            report.add_error(
                rule="break_field_cannot_be_required",
                message=f"Layout break '{field.fieldname}' ({ftype}) cannot have reqd=True.",
                doctype=dt.name,
                field=field.fieldname,
            )

        # Check consecutive duplicate breaks
        if is_break and ftype == last_type:
            report.add_warning(
                rule="consecutive_break_fields",
                message=f"Consecutive {ftype} fields in DocType '{dt.name}' without fields in between.",
                doctype=dt.name,
                field=field.fieldname,
            )

        last_type = ftype if is_break else None


def validate_workflows(
    workflows: list[WorkflowSpec],
    doctypes_map: dict[str, DocTypeSpec],
    app_roles: list[str],
    report: ValidationReport,
) -> None:
    """
    Deterministic rules WF001 through WF011 for Frappe v15 workflows.
    """
    # WF008: at most one workflow per document_type
    seen_wf_doctypes: dict[str, str] = {}
    for wf in workflows:
        if wf.document_type in seen_wf_doctypes:
            report.add_error(
                rule="workflow_multiple_per_doctype",
                rule_id="WF008",
                path=f"workflows/{wf.name}",
                doctype=wf.document_type,
                message=f"At most one workflow allowed per document_type; duplicate workflow '{wf.name}' for '{wf.document_type}' (first: '{seen_wf_doctypes[wf.document_type]}').",
            )
        else:
            seen_wf_doctypes[wf.document_type] = wf.name

    for wf_idx, wf in enumerate(workflows):
        wf_path = f"app/workflows/{wf_idx}"
        target_dt = doctypes_map.get(wf.document_type)

        state_names = {s.state for s in wf.states}
        state_map = {s.state: s for s in wf.states}

        # WF001: every transition.state and next_state exists in states[]
        for t_idx, t in enumerate(wf.transitions):
            t_path = f"{wf_path}/transitions/{t_idx}"
            if t.state not in state_names:
                report.add_error(
                    rule="workflow_unknown_source_state",
                    rule_id="WF001",
                    path=f"{t_path}/state",
                    doctype=wf.document_type,
                    message=f"Transition state '{t.state}' does not exist in workflow states list.",
                    fix_hint=FixHint(
                        rule="WF001",
                        rule_id="WF001",
                        path=f"{wf_path}/states",
                        doctype=wf.document_type,
                        message=f"Add missing state '{t.state}' to workflow states.",
                        suggested_patch={
                            "op": "add",
                            "path": f"/{wf_path}/states/-",
                            "value": {"state": t.state, "doc_status": 0, "style": "", "allow_edit": "System Manager"},
                        },
                    ),
                )
            if t.next_state not in state_names:
                report.add_error(
                    rule="workflow_unknown_next_state",
                    rule_id="WF001",
                    path=f"{t_path}/next_state",
                    doctype=wf.document_type,
                    message=f"Transition next_state '{t.next_state}' does not exist in workflow states list.",
                    fix_hint=FixHint(
                        rule="WF001",
                        rule_id="WF001",
                        path=f"{wf_path}/states",
                        doctype=wf.document_type,
                        message=f"Add missing state '{t.next_state}' to workflow states.",
                        suggested_patch={
                            "op": "add",
                            "path": f"/{wf_path}/states/-",
                            "value": {"state": t.next_state, "doc_status": 0, "style": "", "allow_edit": "System Manager"},
                        },
                    ),
                )

        # Incoming transitions analysis for WF002 and WF003
        incoming_counts: dict[str, int] = dict.fromkeys(state_names, 0)
        for t in wf.transitions:
            if t.next_state in incoming_counts:
                incoming_counts[t.next_state] += 1

        zero_incoming = [s for s, count in incoming_counts.items() if count == 0]
        first_state = wf.states[0].state if wf.states else None

        # WF002: exactly one initial state (no incoming transitions) and it has doc_status 0
        if len(zero_incoming) != 1:
            report.add_error(
                rule="workflow_initial_state_count",
                rule_id="WF002",
                path=f"{wf_path}/states",
                doctype=wf.document_type,
                message=f"Workflow must have exactly one initial state with no incoming transitions; found {len(zero_incoming)} ({sorted(zero_incoming)}).",
            )
        elif first_state and incoming_counts.get(first_state, 0) > 0:
            report.add_error(
                rule="workflow_initial_state_incoming",
                rule_id="WF002",
                path=f"{wf_path}/states/0",
                doctype=wf.document_type,
                message=f"Initial state '{first_state}' must have 0 incoming transitions.",
            )

        if zero_incoming:
            init_state = state_map.get(zero_incoming[0])
            if init_state and init_state.doc_status != 0:
                report.add_error(
                    rule="workflow_initial_state_doc_status",
                    rule_id="WF002",
                    path=f"{wf_path}/states",
                    doctype=wf.document_type,
                    message=f"Initial state '{init_state.state}' must have doc_status 0 (Draft), got {init_state.doc_status}.",
                    fix_hint=FixHint(
                        rule="WF002",
                        rule_id="WF002",
                        path=f"{wf_path}/states",
                        doctype=wf.document_type,
                        message=f"Set doc_status of initial state '{init_state.state}' to 0.",
                    ),
                )

        # WF003: no unreachable state (every non-initial state has >= 1 incoming transition)
        for idx, s in enumerate(wf.states):
            if idx > 0 and incoming_counts.get(s.state, 0) == 0:
                report.add_error(
                    rule="workflow_unreachable_state",
                    rule_id="WF003",
                    path=f"{wf_path}/states/{idx}",
                    doctype=wf.document_type,
                    message=f"Unreachable state '{s.state}': non-initial state has no incoming transitions.",
                )

        # WF004: every allowed / allow_edit role exists in app.roles AND has a permission row on document_type
        roles_set = set(app_roles)
        roles_set.add("System Manager")  # Standard built-in role
        dt_perm_roles = {p.role for p in target_dt.permissions} if target_dt else set()

        for s_idx, s in enumerate(wf.states):
            if s.allow_edit:
                if s.allow_edit not in roles_set:
                    report.add_error(
                        rule="workflow_role_not_in_app",
                        rule_id="WF004",
                        path=f"{wf_path}/states/{s_idx}/allow_edit",
                        doctype=wf.document_type,
                        message=f"Role '{s.allow_edit}' in state allow_edit does not exist in app.roles.",
                        fix_hint=FixHint(
                            rule="WF004",
                            rule_id="WF004",
                            path="app/roles",
                            doctype=wf.document_type,
                            message=f"Add role '{s.allow_edit}' to app.roles.",
                            suggested_patch={"op": "add", "path": "/app/roles/-", "value": s.allow_edit},
                        ),
                    )
                if target_dt and s.allow_edit not in dt_perm_roles:
                    report.add_error(
                        rule="workflow_role_missing_permission",
                        rule_id="WF004",
                        path=f"app/doctypes/{target_dt.name}/permissions",
                        doctype=wf.document_type,
                        message=f"Role '{s.allow_edit}' in state allow_edit has no permission row on DocType '{target_dt.name}'.",
                        fix_hint=FixHint(
                            rule="WF004",
                            rule_id="WF004",
                            path=f"app/doctypes/{target_dt.name}/permissions",
                            doctype=target_dt.name,
                            message=f"Add permission row for role '{s.allow_edit}' on DocType '{target_dt.name}'.",
                            suggested_patch={
                                "op": "add",
                                "path": f"/app/doctypes/{target_dt.name}/permissions/-",
                                "value": {"role": s.allow_edit, "read": True, "write": True, "create": False, "delete": False},
                            },
                        ),
                    )

        for t_idx, t in enumerate(wf.transitions):
            if t.allowed:
                if t.allowed not in roles_set:
                    report.add_error(
                        rule="workflow_role_not_in_app",
                        rule_id="WF004",
                        path=f"{wf_path}/transitions/{t_idx}/allowed",
                        doctype=wf.document_type,
                        message=f"Role '{t.allowed}' in transition allowed does not exist in app.roles.",
                        fix_hint=FixHint(
                            rule="WF004",
                            rule_id="WF004",
                            path="app/roles",
                            doctype=wf.document_type,
                            message=f"Add role '{t.allowed}' to app.roles.",
                            suggested_patch={"op": "add", "path": "/app/roles/-", "value": t.allowed},
                        ),
                    )
                if target_dt and t.allowed not in dt_perm_roles:
                    report.add_error(
                        rule="workflow_role_missing_permission",
                        rule_id="WF004",
                        path=f"app/doctypes/{target_dt.name}/permissions",
                        doctype=wf.document_type,
                        message=f"Role '{t.allowed}' in transition allowed has no permission row on DocType '{target_dt.name}'.",
                        fix_hint=FixHint(
                            rule="WF004",
                            rule_id="WF004",
                            path=f"app/doctypes/{target_dt.name}/permissions",
                            doctype=target_dt.name,
                            message=f"Add permission row for role '{t.allowed}' on DocType '{target_dt.name}'.",
                            suggested_patch={
                                "op": "add",
                                "path": f"/app/doctypes/{target_dt.name}/permissions/-",
                                "value": {"role": t.allowed, "read": True, "write": False, "create": False, "delete": False},
                            },
                        ),
                    )

        # WF005: workflow_state_field exists on document_type, fieldtype Select or Link(Workflow State), read_only 1
        wf_field_name = wf.workflow_state_field or "workflow_state"
        if target_dt:
            wf_field = next((f for f in target_dt.fields if f.fieldname == wf_field_name), None)
            expected_options = "\n".join(s.state for s in wf.states)
            if not wf_field:
                report.add_error(
                    rule="workflow_state_field_missing",
                    rule_id="WF005",
                    path=f"app/doctypes/{target_dt.name}/fields",
                    doctype=target_dt.name,
                    field=wf_field_name,
                    message=f"workflow_state_field '{wf_field_name}' does not exist on DocType '{target_dt.name}'.",
                    fix_hint=FixHint(
                        rule="WF005",
                        rule_id="WF005",
                        path=f"app/doctypes/{target_dt.name}/fields",
                        doctype=target_dt.name,
                        field=wf_field_name,
                        message=f"Add '{wf_field_name}' field to DocType '{target_dt.name}'.",
                        suggested_patch={
                            "op": "add",
                            "path": f"/app/doctypes/{target_dt.name}/fields/-",
                            "value": {
                                "fieldname": wf_field_name,
                                "label": "Workflow State",
                                "fieldtype": "Select",
                                "options": expected_options,
                                "read_only": True,
                                "in_list_view": True,
                                "in_standard_filter": True,
                            },
                        },
                    ),
                )
            else:
                if wf_field.fieldtype not in ("Select", "Link") or (
                    wf_field.fieldtype == "Link" and wf_field.options != "Workflow State"
                ):
                    report.add_error(
                        rule="workflow_state_field_type_invalid",
                        rule_id="WF005",
                        path=f"app/doctypes/{target_dt.name}/fields/{wf_field_name}/fieldtype",
                        doctype=target_dt.name,
                        field=wf_field_name,
                        message=f"Field '{wf_field_name}' must be Select or Link (options: 'Workflow State'), got {wf_field.fieldtype}.",
                    )
                if not wf_field.read_only:
                    report.add_error(
                        rule="workflow_state_field_not_readonly",
                        rule_id="WF005",
                        path=f"app/doctypes/{target_dt.name}/fields/{wf_field_name}/read_only",
                        doctype=target_dt.name,
                        field=wf_field_name,
                        message=f"Field '{wf_field_name}' must have read_only == 1.",
                        fix_hint=FixHint(
                            rule="WF005",
                            rule_id="WF005",
                            path=f"app/doctypes/{target_dt.name}/fields/{wf_field_name}/read_only",
                            doctype=target_dt.name,
                            field=wf_field_name,
                            message=f"Set read_only: true on field '{wf_field_name}'.",
                        ),
                    )

                # WF011: Select options of workflow_state field exactly equal the set of state names
                if wf_field.fieldtype == "Select":
                    raw_opts = (wf_field.options or "").strip().split("\n")
                    field_opts = {o.strip() for o in raw_opts if o.strip()}
                    if field_opts != state_names:
                        report.add_error(
                            rule="workflow_state_options_mismatch",
                            rule_id="WF011",
                            path=f"app/doctypes/{target_dt.name}/fields/{wf_field_name}/options",
                            doctype=target_dt.name,
                            field=wf_field_name,
                            message=f"Select options on '{wf_field_name}' ({sorted(field_opts)}) do not match workflow states ({sorted(state_names)}).",
                            fix_hint=FixHint(
                                rule="WF011",
                                rule_id="WF011",
                                path=f"app/doctypes/{target_dt.name}/fields/{wf_field_name}/options",
                                doctype=target_dt.name,
                                field=wf_field_name,
                                message=f"Update Select options on '{wf_field_name}' to match state names.",
                                suggested_patch={
                                    "op": "replace",
                                    "path": f"/app/doctypes/{target_dt.name}/fields/{wf_field_name}/options",
                                    "value": expected_options,
                                },
                            ),
                        )

        # WF006: doc_status never decreases along a transition (0->1->2 only; 1->0 is an error)
        for t_idx, t in enumerate(wf.transitions):
            s_from = state_map.get(t.state)
            s_to = state_map.get(t.next_state)
            if s_from and s_to:
                if s_to.doc_status < s_from.doc_status:
                    report.add_error(
                        rule="workflow_doc_status_decreasing",
                        rule_id="WF006",
                        path=f"{wf_path}/transitions/{t_idx}",
                        doctype=wf.document_type,
                        message=f"doc_status cannot decrease along transition '{t.state}' ({s_from.doc_status}) -> '{t.next_state}' ({s_to.doc_status}).",
                    )

        # WF007: if any state doc_status >= 1 then DocType.is_submittable == 1
        has_submittable_state = any(s.doc_status >= 1 for s in wf.states)
        if target_dt and has_submittable_state and not target_dt.is_submittable:
            report.add_error(
                rule="workflow_submittable_mismatch",
                rule_id="WF007",
                path=f"app/doctypes/{target_dt.name}/is_submittable",
                doctype=target_dt.name,
                message=f"DocType '{target_dt.name}' has workflow states with doc_status >= 1, but is_submittable is not 1.",
                fix_hint=FixHint(
                    rule="WF007",
                    rule_id="WF007",
                    path=f"app/doctypes/{target_dt.name}/is_submittable",
                    doctype=target_dt.name,
                    message=f"Set is_submittable: true on DocType '{target_dt.name}'.",
                    suggested_patch={
                        "op": "replace",
                        "path": f"/app/doctypes/{target_dt.name}/is_submittable",
                        "value": True,
                    },
                ),
            )

        # WF009: no duplicate (state, action) pair in transitions
        seen_transitions: set[tuple[str, str]] = set()
        for t_idx, t in enumerate(wf.transitions):
            key = (t.state.strip(), t.action.strip())
            if key in seen_transitions:
                report.add_error(
                    rule="workflow_duplicate_transition",
                    rule_id="WF009",
                    path=f"{wf_path}/transitions/{t_idx}",
                    doctype=wf.document_type,
                    message=f"Duplicate transition for state '{t.state}' and action '{t.action}'.",
                    fix_hint=FixHint(
                        rule="WF009",
                        rule_id="WF009",
                        path=f"{wf_path}/transitions/{t_idx}",
                        doctype=wf.document_type,
                        message=f"Drop duplicate transition '{t.state}' -> '{t.action}'.",
                        suggested_patch={
                            "op": "remove",
                            "path": f"/{wf_path}/transitions/{t_idx}",
                        },
                    ),
                )
            else:
                seen_transitions.add(key)

        # WF010: transition.condition, if present, parses with ast.parse(mode="eval") and references only doc, frappe, user
        ALLOWED_CONDITION_NAMES = {"doc", "frappe", "user", "True", "False", "None"}
        for t_idx, t in enumerate(wf.transitions):
            if t.condition and t.condition.strip():
                cond = t.condition.strip()
                try:
                    tree = ast.parse(cond, mode="eval")
                    names_used = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
                    disallowed = names_used - ALLOWED_CONDITION_NAMES
                    if disallowed:
                        report.add_error(
                            rule="workflow_condition_disallowed_identifier",
                            rule_id="WF010",
                            path=f"{wf_path}/transitions/{t_idx}/condition",
                            doctype=wf.document_type,
                            message=f"Transition condition '{cond}' references disallowed identifiers: {sorted(disallowed)}. Allowed: doc, frappe, user.",
                        )
                except SyntaxError as e:
                    report.add_error(
                        rule="workflow_condition_syntax_error",
                        rule_id="WF010",
                        path=f"{wf_path}/transitions/{t_idx}/condition",
                        doctype=wf.document_type,
                        message=f"Transition condition '{cond}' is not valid Python syntax: {e}.",
                    )


def validate_circular_mandatory_links(
    doctypes: list[DocTypeSpec], report: ValidationReport
) -> None:
    """Detect impossible mandatory link insertion cycles between DocTypes."""
    # Graph: DocType -> set of target DocTypes required on create
    req_links: dict[str, set[str]] = {}
    for dt in doctypes:
        if dt.istable:
            continue
        targets = set()
        for f in dt.fields:
            if f.fieldtype == "Link" and f.reqd and f.options:
                targets.add(f.options)
        req_links[dt.name] = targets

    for dt_a, targets in req_links.items():
        for dt_b in targets:
            if dt_b in req_links and dt_a in req_links[dt_b]:
                report.add_error(
                    rule="circular_mandatory_link",
                    message=(
                        f"Circular mandatory link detected between '{dt_a}' and '{dt_b}'. "
                        f"Neither can be inserted first; make at least one of these links optional."
                    ),
                    doctype=dt_a,
                )
