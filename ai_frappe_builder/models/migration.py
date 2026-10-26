"""
migration.py — Seamless deterministic migration from AppSpec 1.0 to AppSpec 2.0.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from ai_frappe_builder.models.app_spec_v2 import (
    AppMetadata,
    AppSpecV2,
    ClientScriptSpec,
    DocTypeKind,
    DocTypeSpec,
    FieldSpec,
    InterviewQuestion,
    PermissionSpec,
    QuestionOption,
    ReportSpec,
    ServerScriptSpec,
    WorkflowSpec,
    WorkflowState,
    WorkflowTransition,
)


def _to_snake_case(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    return re.sub(r"[\s-]+", "_", s) or "custom_app"


def normalize_workflows(spec: AppSpecV2) -> AppSpecV2:
    """Post-processing normalization ensuring idiomatic, valid Frappe v15 workflows."""
    if not spec.app:
        return spec

    app = spec.app
    roles_set = set(app.roles)

    # 1. Synthesize workflow for any DocType with a lifecycle if none exists
    existing_wf_doctypes = {wf.document_type for wf in app.workflows}
    for dt in app.doctypes:
        if dt.istable or dt.name in existing_wf_doctypes:
            continue
        status_field = next(
            (f for f in dt.fields if f.fieldname == "status" and f.fieldtype == "Select" and f.options),
            None,
        )
        if status_field and status_field.options:
            raw_options = [opt.strip() for opt in status_field.options.splitlines() if opt.strip()]
            if len(raw_options) >= 2:
                primary_role = app.roles[0] if app.roles else "System Manager"
                states: list[WorkflowState] = []
                transitions: list[WorkflowTransition] = []
                for idx, opt in enumerate(raw_options):
                    is_sub = (
                        1
                        if (dt.is_submittable and idx > 0)
                        or any(w in opt.lower() for w in ["submit", "approv", "active", "closed", "complet"])
                        else 0
                    )
                    if any(w in opt.lower() for w in ["cancel", "reject"]):
                        is_sub = 2 if dt.is_submittable else 0
                    style = "Success" if is_sub == 1 else ("Danger" if is_sub == 2 else "")
                    states.append(
                        WorkflowState(
                            state=opt,
                            doc_status=is_sub,
                            style=style,
                            allow_edit=primary_role,
                        )
                    )
                    if idx > 0:
                        transitions.append(
                            WorkflowTransition(
                                state=raw_options[idx - 1],
                                action=f"Mark as {opt}",
                                next_state=opt,
                                allowed=primary_role,
                            )
                        )
                app.workflows.append(
                    WorkflowSpec(
                        name=f"{dt.name} Workflow",
                        document_type=dt.name,
                        workflow_state_field="workflow_state",
                        is_active=1,
                        states=states,
                        transitions=transitions,
                    )
                )

    # 2. Normalize all workflows
    for wf in app.workflows:
        dt = next((d for d in app.doctypes if d.name == wf.document_type), None)
        if not dt:
            continue

        state_names = [s.state for s in wf.states]
        has_submittable = any(s.doc_status >= 1 for s in wf.states)

        # DocType.is_submittable must be True if any state doc_status >= 1
        if has_submittable:
            dt.is_submittable = True

        # Remove hand-rolled status Select field duplicating workflow states
        dt.fields = [
            f
            for f in dt.fields
            if not (
                f.fieldname == "status"
                and (f.fieldtype == "Select" or set((f.options or "").splitlines()) == set(state_names))
            )
        ]

        # Ensure workflow_state field exists with correct configuration
        wf_field_name = wf.workflow_state_field or "workflow_state"
        wf_field = next((f for f in dt.fields if f.fieldname == wf_field_name), None)
        newline_options = "\n".join(state_names)
        if wf_field:
            wf_field.fieldtype = "Select"
            wf_field.options = newline_options
            wf_field.read_only = True
            wf_field.in_list_view = True
            wf_field.in_standard_filter = True
            if has_submittable:
                wf_field.allow_on_submit = True
        else:
            dt.fields.append(
                FieldSpec(
                    fieldname=wf_field_name,
                    label="Workflow State",
                    fieldtype="Select",
                    options=newline_options,
                    read_only=True,
                    in_list_view=True,
                    in_standard_filter=True,
                    allow_on_submit=has_submittable,
                )
            )

        # Collect roles and check permissions
        allow_edit_roles = {s.allow_edit for s in wf.states if s.allow_edit}
        state_doc_status = {s.state: s.doc_status for s in wf.states}
        submit_roles = {
            t.allowed
            for t in wf.transitions
            if state_doc_status.get(t.next_state, 0) == 1 and t.allowed
        }
        cancel_roles = {
            t.allowed
            for t in wf.transitions
            if state_doc_status.get(t.next_state, 0) == 2 and t.allowed
        }
        all_wf_roles = allow_edit_roles | {t.allowed for t in wf.transitions if t.allowed}

        for role in all_wf_roles:
            if role not in roles_set:
                app.roles.append(role)
                roles_set.add(role)

        existing_perm_roles = {p.role: p for p in dt.permissions}
        for role in all_wf_roles:
            is_write = role in allow_edit_roles
            is_submit = role in submit_roles
            is_cancel = role in cancel_roles

            if role in existing_perm_roles:
                perm = existing_perm_roles[role]
                perm.read = True
                if is_write:
                    perm.write = True
                if is_submit:
                    perm.submit = True
                if is_cancel:
                    perm.cancel = True
            else:
                dt.permissions.append(
                    PermissionSpec(
                        role=role,
                        read=True,
                        write=is_write,
                        create=is_write,
                        submit=is_submit,
                        cancel=is_cancel,
                    )
                )

    return spec


def migrate_v1_to_v2(raw: dict[str, Any]) -> AppSpecV2:
    """
    Deterministically transforms a legacy 1.0 AppSpec dictionary into an authoritative AppSpecV2.
    """
    version = str(raw.get("spec_version", "1.0"))
    if version == "2.0":
        spec = AppSpecV2.model_validate(raw)
        return normalize_workflows(spec)

    status = raw.get("status", "needs_input")
    if status not in {"ready", "needs_input", "drafting", "validating", "failed"}:
        status = "ready" if raw.get("app") else "needs_input"

    assumptions = [str(a) for a in raw.get("assumptions", [])]

    # Convert legacy questions
    questions: list[InterviewQuestion] = []
    raw_questions = raw.get("questions", [])
    for idx, q in enumerate(raw_questions):
        if isinstance(q, str):
            questions.append(
                InterviewQuestion(
                    id=f"q_{idx}_{uuid.uuid4().hex[:6]}",
                    question=q,
                    options=[],
                )
            )
        elif isinstance(q, dict):
            qid = q.get("id") or f"q_{idx}_{uuid.uuid4().hex[:6]}"
            q_text = q.get("question") or q.get("text") or str(q)
            q_reason = q.get("reason")
            opts = []
            for opt in q.get("options", []):
                if isinstance(opt, str):
                    opts.append(QuestionOption(label=opt, value=opt))
                elif isinstance(opt, dict):
                    opts.append(
                        QuestionOption(
                            label=opt.get("label", ""), value=opt.get("value", opt.get("label", ""))
                        )
                    )
            questions.append(
                InterviewQuestion(id=qid, question=q_text, reason=q_reason, options=opts)
            )

    raw_app = raw.get("app")
    app_meta: AppMetadata | None = None

    if raw_app and isinstance(raw_app, dict):
        raw_name = raw_app.get("app_name") or raw_app.get("name") or "custom_app"
        app_name = _to_snake_case(raw_name)
        title = raw_app.get("title") or app_name.replace("_", " ").title()
        modules = raw_app.get("modules") or ["Custom"]
        default_module = modules[0] if modules else "Custom"

        # Migrate DocTypes
        doctypes: list[DocTypeSpec] = []
        for dt in raw_app.get("doctypes", []):
            d = dict(dt)
            dt_name = d.get("name") or d.get("doctype") or d.get("title") or "UnnamedDocType"
            # Title Case guarantee
            dt_name = " ".join(word.capitalize() for word in dt_name.split())
            module = d.get("module") or default_module
            istable = bool(d.get("istable", False))
            is_submittable = bool(d.get("is_submittable", False))
            is_single = bool(d.get("is_single", False))
            track_changes = bool(d.get("track_changes", False))
            autoname = d.get("autoname") or ("hash" if istable else "Prompt")
            kind_str = d.get("kind")
            if kind_str in {k.value for k in DocTypeKind}:
                kind = DocTypeKind(kind_str)
            else:
                kind = DocTypeKind.CHILD if istable else DocTypeKind.MASTER

            # Clean fields
            fields: list[FieldSpec] = []
            for f in d.get("fields", []):
                fd = dict(f)
                fname = _to_snake_case(fd.get("fieldname") or "field")
                flabel = fd.get("label") or fname.replace("_", " ").title()
                ftype = fd.get("fieldtype") or "Data"
                options = fd.get("options")
                fields.append(
                    FieldSpec(
                        fieldname=fname,
                        label=flabel,
                        fieldtype=ftype,
                        options=options,
                        reqd=bool(fd.get("reqd", False)),
                        unique=bool(fd.get("unique", False)),
                        read_only=bool(fd.get("read_only", False)),
                        hidden=bool(fd.get("hidden", False)),
                        in_list_view=bool(fd.get("in_list_view", False)),
                        in_standard_filter=bool(fd.get("in_standard_filter", False)),
                        default=fd.get("default"),
                        fetch_from=fd.get("fetch_from"),
                        depends_on=fd.get("depends_on"),
                        description=fd.get("description"),
                    )
                )

            # Clean permissions
            permissions: list[PermissionSpec] = []
            for p in d.get("permissions", []):
                pd = dict(p)
                role = pd.get("role", "System Manager")
                permissions.append(
                    PermissionSpec(
                        role=role,
                        read=bool(pd.get("read", True)),
                        write=bool(pd.get("write", False)),
                        create=bool(pd.get("create", False)),
                        delete=bool(pd.get("delete", False)),
                        submit=bool(pd.get("submit", False)),
                        cancel=bool(pd.get("cancel", False)),
                        amend=bool(pd.get("amend", False)),
                        report=bool(pd.get("report", False)),
                        export=bool(pd.get("export", False)),
                        import_=bool(pd.get("import", pd.get("import_", False))),
                    )
                )
            if not permissions and not istable:
                permissions.append(
                    PermissionSpec(
                        role="System Manager", read=True, write=True, create=True, delete=True
                    )
                )

            doctypes.append(
                DocTypeSpec(
                    name=dt_name,
                    module=module,
                    kind=kind,
                    istable=istable,
                    is_submittable=is_submittable,
                    is_single=is_single,
                    track_changes=track_changes,
                    autoname=autoname,
                    title_field=d.get("title_field"),
                    search_fields=d.get("search_fields", []),
                    description=d.get("description"),
                    fields=fields,
                    permissions=permissions,
                )
            )

        # Migrate Workflows
        workflows: list[WorkflowSpec] = []
        for wf in raw_app.get("workflows", []):
            wd = dict(wf)
            w_name = wd.get("name") or "Workflow"
            doc_type = wd.get("document_type") or wd.get("doctype") or wd.get("ref_doctype") or ""
            states: list[WorkflowState] = []
            for s in wd.get("states", []):
                sd = dict(s)
                if "doc_status" in sd:
                    d_status = int(sd["doc_status"])
                else:
                    status_str = str(sd.get("docs", "")).lower()
                    if "cancel" in status_str:
                        d_status = 2
                    elif (
                        "submit" in status_str or "complete" in status_str or "active" in status_str
                    ):
                        d_status = 1
                    else:
                        d_status = 0
                allow_edit = sd.get("allow_edit", "System Manager")
                raw_style = str(sd.get("style", "")).capitalize()
                style_val = raw_style if raw_style in ("Success", "Warning", "Danger", "Primary") else ""
                states.append(
                    WorkflowState(
                        state=sd.get("state", "Draft"),
                        doc_status=d_status,
                        style=style_val,
                        allow_edit=allow_edit,
                        update_field=sd.get("update_field"),
                        update_value=sd.get("update_value"),
                    )
                )

            transitions: list[WorkflowTransition] = []
            for t in wd.get("transitions", []):
                td = dict(t)
                allowed = td.get("allowed") or td.get("allow_role") or "System Manager"
                allow_self = 1 if td.get("allow_self_approval", 1) in (1, True, "1") else 0
                transitions.append(
                    WorkflowTransition(
                        state=td.get("state", "Draft"),
                        action=td.get("action", "Submit"),
                        next_state=td.get("next_state", "Approved"),
                        allowed=allowed,
                        condition=td.get("condition"),
                        allow_self_approval=allow_self,
                    )
                )

            workflows.append(
                WorkflowSpec(
                    name=w_name,
                    document_type=doc_type,
                    workflow_state_field=wd.get("workflow_state_field", "workflow_state"),
                    is_active=1 if wd.get("is_active", 1) in (1, True, "1") else 0,
                    states=states,
                    transitions=transitions,
                )
            )

        default_ref_dt = doctypes[0].name if doctypes else "DocType"

        # Migrate Scripts and Reports with resilient field normalization
        server_scripts: list[ServerScriptSpec] = []
        for s in raw_app.get("server_scripts", []):
            if isinstance(s, dict):
                ref_dt = (
                    s.get("reference_doctype")
                    or s.get("doctype")
                    or s.get("document_type")
                    or s.get("ref_doctype")
                    or default_ref_dt
                )
                server_scripts.append(
                    ServerScriptSpec(
                        name=s.get("name", "custom_server_script"),
                        script_type=s.get("script_type", "DocType Event"),
                        reference_doctype=ref_dt,
                        doctype_event=s.get("doctype_event", "Before Save"),
                        purpose=s.get("purpose", "Custom logic"),
                        pattern=s.get("pattern", "custom"),
                        script=s.get("script"),
                    )
                )

        client_scripts: list[ClientScriptSpec] = []
        for s in raw_app.get("client_scripts", []):
            if isinstance(s, dict):
                ref_dt = (
                    s.get("reference_doctype")
                    or s.get("doctype")
                    or s.get("document_type")
                    or s.get("ref_doctype")
                    or default_ref_dt
                )
                client_scripts.append(
                    ClientScriptSpec(
                        name=s.get("name", "custom_client_script"),
                        reference_doctype=ref_dt,
                        view=s.get("view", "Form"),
                        purpose=s.get("purpose", "UI enhancement"),
                        pattern=s.get("pattern", "custom"),
                        script=s.get("script"),
                    )
                )

        reports: list[ReportSpec] = []
        for r in raw_app.get("reports", []):
            if isinstance(r, dict):
                ref_dt = (
                    r.get("ref_doctype")
                    or r.get("reference_doctype")
                    or r.get("doctype")
                    or r.get("document_type")
                    or default_ref_dt
                )
                reports.append(
                    ReportSpec(
                        name=r.get("name", "Custom Report"),
                        ref_doctype=ref_dt,
                        report_type=r.get("report_type", "Script Report"),
                        columns=r.get("columns", []),
                        filters=r.get("filters", []),
                        script=r.get("script"),
                        query=r.get("query"),
                    )
                )

        app_meta = AppMetadata(
            app_name=app_name,
            title=title,
            description=raw_app.get("description", "Custom Frappe application"),
            publisher=raw_app.get("publisher", "Frappe Builder"),
            email=raw_app.get("email", "developer@example.com"),
            license=raw_app.get("license", "MIT"),
            version=raw_app.get("version", "0.0.1"),
            requires_erpnext=bool(raw_app.get("requires_erpnext", False)),
            modules=modules,
            roles=raw_app.get("roles", ["System Manager"]),
            doctypes=doctypes,
            workflows=workflows,
            server_scripts=server_scripts,
            client_scripts=client_scripts,
            reports=reports,
        )

    spec = AppSpecV2(
        spec_version="2.0",
        status=status,
        archetype=raw.get("archetype"),
        questions=questions,
        assumptions=assumptions,
        app=app_meta,
    )
    return normalize_workflows(spec)
