"""
rules.py — Deterministic Frappe schema validation rules.
"""

from __future__ import annotations

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
    report: ValidationReport,
) -> None:
    """Rule 8, 9 & Submittable consistency."""
    for wf in workflows:
        # Check minimum states and transitions
        if len(wf.states) < 2:
            report.add_error(
                rule="workflow_insufficient_states",
                message=f"Workflow '{wf.name}' must have at least 2 states, got {len(wf.states)}.",
            )
        if len(wf.transitions) < 1:
            report.add_error(
                rule="workflow_insufficient_transitions",
                message=f"Workflow '{wf.name}' must have at least 1 transition, got {len(wf.transitions)}.",
            )

        state_names = {s.state for s in wf.states}
        has_submitted_state = False

        for s in wf.states:
            if s.doc_status not in (0, 1, 2):
                report.add_error(
                    rule="workflow_invalid_doc_status",
                    message=f"Workflow '{wf.name}' state '{s.state}' has invalid doc_status {s.doc_status} (must be 0, 1, or 2).",
                )
            if s.doc_status == 1:
                has_submitted_state = True

        for t in wf.transitions:
            if t.state not in state_names:
                report.add_error(
                    rule="workflow_unknown_source_state",
                    message=f"Workflow '{wf.name}' transition source state '{t.state}' is not defined in states.",
                )
            if t.next_state not in state_names:
                report.add_error(
                    rule="workflow_unknown_next_state",
                    message=f"Workflow '{wf.name}' transition next_state '{t.next_state}' is not defined in states.",
                )

        # Cross check is_submittable with target doctype
        target_dt = doctypes_map.get(wf.document_type)
        if target_dt:
            if has_submitted_state and not target_dt.is_submittable:
                report.add_error(
                    rule="workflow_submittable_mismatch",
                    message=(
                        f"DocType '{target_dt.name}' has a workflow with doc_status=1 (Submitted), "
                        f"but is_submittable is false."
                    ),
                    doctype=target_dt.name,
                    fix_hint=FixHint(
                        rule="workflow_submittable_mismatch",
                        doctype=target_dt.name,
                        message="Set is_submittable: true on DocType.",
                    ),
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
