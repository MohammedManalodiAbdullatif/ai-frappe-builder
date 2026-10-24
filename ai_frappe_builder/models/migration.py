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


def migrate_v1_to_v2(raw: dict[str, Any]) -> AppSpecV2:
    """
    Deterministically transforms a legacy 1.0 AppSpec dictionary into an authoritative AppSpecV2.
    """
    version = str(raw.get("spec_version", "1.0"))
    if version == "2.0":
        return AppSpecV2.model_validate(raw)

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
                states.append(
                    WorkflowState(
                        state=sd.get("state", "Draft"), doc_status=d_status, allow_edit=allow_edit
                    )
                )

            transitions: list[WorkflowTransition] = []
            for t in wd.get("transitions", []):
                td = dict(t)
                allowed = td.get("allowed") or td.get("allow_role") or "System Manager"
                transitions.append(
                    WorkflowTransition(
                        state=td.get("state", "Draft"),
                        action=td.get("action", "Submit"),
                        next_state=td.get("next_state", "Approved"),
                        allowed=allowed,
                        condition=td.get("condition"),
                    )
                )

            workflows.append(
                WorkflowSpec(
                    name=w_name,
                    document_type=doc_type,
                    workflow_state_field=wd.get("workflow_state_field", "workflow_state"),
                    is_active=bool(wd.get("is_active", True)),
                    states=states,
                    transitions=transitions,
                )
            )

        # Migrate Scripts and Reports
        server_scripts = [ServerScriptSpec(**s) for s in raw_app.get("server_scripts", [])]
        client_scripts = [ClientScriptSpec(**s) for s in raw_app.get("client_scripts", [])]
        reports = [ReportSpec(**r) for r in raw_app.get("reports", [])]

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

    return AppSpecV2(
        spec_version="2.0",
        status=status,
        archetype=raw.get("archetype"),
        questions=questions,
        assumptions=assumptions,
        app=app_meta,
    )
