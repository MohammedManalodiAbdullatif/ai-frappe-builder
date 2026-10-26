"""
applier.py — Translate an AppSpec into live Frappe DocTypes/Workflows.

Apply order (important — dependencies must come first):
  1. Roles
  2. Child DocTypes  (istable=True) — transactions reference them
  3. Settings / Master DocTypes
  4. Transaction DocTypes
  5. Log DocTypes
  6. Workflows
  7. Sample data (best-effort)

All operations are logged to the console and errors are collected without
raising so the caller gets a full picture of what succeeded and what failed.
"""

from __future__ import annotations

import logging
from typing import Any

import report_builder
import run_tests
import script_generator
from frappe_client import FrappeAPIError, FrappeClient
from models import (
    AppSpec,
    ClientScriptSpec,
    DocTypeSpec,
    PermissionSpec,
    ServerScriptSpec,
    WorkflowSpec,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DocType → Frappe wire format
# ---------------------------------------------------------------------------


def _permission_to_frappe(p: PermissionSpec) -> dict:
    return {
        "role": p.role,
        "read": 1 if p.read else 0,
        "write": 1 if p.write else 0,
        "create": 1 if p.create else 0,
        "delete": 1 if p.delete else 0,
        "submit": 1 if p.submit else 0,
        "cancel": 1 if p.cancel else 0,
        "amend": 1 if p.amend else 0,
        "report": 1 if p.report else 0,
        "export": 1 if p.export else 0,
        "import": 1 if p.import_ else 0,
    }


def _doctype_to_frappe(spec: DocTypeSpec) -> dict:
    """Convert a DocTypeSpec pydantic model to Frappe REST API wire format."""
    fields_payload = []
    for f in spec.fields:
        field_dict: dict[str, Any] = {
            "fieldname": f.fieldname,
            "label": f.label,
            "fieldtype": f.fieldtype,
            "reqd": 1 if f.reqd else 0,
            "unique": 1 if f.unique else 0,
            "read_only": 1 if f.read_only else 0,
            "hidden": 1 if f.hidden else 0,
            "in_list_view": 1 if f.in_list_view else 0,
            "in_standard_filter": 1 if f.in_standard_filter else 0,
        }
        if f.options is not None:
            field_dict["options"] = f.options
        if f.default is not None:
            field_dict["default"] = f.default
        if f.fetch_from is not None:
            field_dict["fetch_from"] = f.fetch_from
        if f.depends_on is not None:
            field_dict["depends_on"] = f.depends_on
        fields_payload.append(field_dict)

    payload: dict[str, Any] = {
        "doctype": "DocType",
        "name": spec.name,
        "module": spec.module,
        "istable": 1 if spec.istable else 0,
        "is_submittable": 1 if spec.is_submittable else 0,
        "is_single": 1 if spec.is_single else 0,
        "track_changes": 1 if spec.track_changes else 0,
        "autoname": spec.autoname,
        "fields": fields_payload,
    }

    if spec.naming_series_options:
        payload["naming_series_options"] = spec.naming_series_options
    if spec.title_field:
        payload["title_field"] = spec.title_field

    if not spec.istable and spec.permissions:
        payload["permissions"] = [_permission_to_frappe(p) for p in spec.permissions]

    return payload


def _workflow_to_frappe(spec: WorkflowSpec) -> dict:
    """Convert a WorkflowSpec to Frappe REST API wire format."""
    states_payload = [
        {
            "state": s.state,
            "doc_status": str(s.doc_status),
            "allow_edit": s.allow_edit,
            "is_optional_state": 1 if s.is_optional_state else 0,
        }
        for s in spec.states
    ]
    transitions_payload = [
        {
            "state": t.state,
            "action": t.action,
            "next_state": t.next_state,
            "allowed": t.allowed,
            **({"condition": t.condition} if t.condition else {}),
        }
        for t in spec.transitions
    ]
    return {
        "doctype": "Workflow",
        "name": spec.name,
        "document_type": spec.document_type,
        "workflow_state_field": spec.workflow_state_field,
        "is_active": 1 if spec.is_active else 0,
        "send_email_alert": 1 if spec.send_email_alert else 0,
        "states": states_payload,
        "transitions": transitions_payload,
    }


def _kebab(name: str) -> str:
    """Convert 'My DocType' → 'my-doctype' for preview URLs."""
    return name.lower().replace(" ", "-")


# ---------------------------------------------------------------------------
# Main applier
# ---------------------------------------------------------------------------


async def apply_spec(
    session_id: str,
    spec: AppSpec,
    frappe_client: FrappeClient,
) -> dict:
    """
    Apply the given AppSpec to the Frappe site.

    Returns a summary dict:
      {
        "status": "done" | "partial" | "failed",
        "created": [list of names],
        "errors": [list of error strings],
        "preview_urls": [list of URLs],
      }
    """
    created: list[str] = []
    errors: list[str] = []
    preview_urls: list[str] = []

    if spec.status != "ready" or spec.app is None:
        return {
            "status": "failed",
            "created": [],
            "errors": ["Spec is not ready — cannot apply."],
            "preview_urls": [],
        }

    frappe_url = frappe_client.base_url

    # --- Parse lists ---
    try:
        doctypes: list[DocTypeSpec] = spec.get_doctypes()
        workflows: list[WorkflowSpec] = spec.get_workflows()
    except Exception as exc:
        return {
            "status": "failed",
            "created": [],
            "errors": [f"Could not parse spec: {exc}"],
            "preview_urls": [],
        }

    app_roles: list[str] = (
        spec.app.get("roles", [])
        if isinstance(spec.app, dict)
        else (spec.app.roles if spec.app else [])
    )
    sample_data: dict = (
        spec.app.get("sample_data", {})
        if isinstance(spec.app, dict)
        else (getattr(spec.app, "sample_data", {}) if spec.app else {})
    )

    # ---------------------------------------------------------------
    # Step 0 — Ensure Modules Exist
    # ---------------------------------------------------------------
    app_modules: set[str] = set()
    if isinstance(spec.app, dict):
        app_modules.update(spec.app.get("modules") or [])
    elif spec.app:
        app_modules.update(spec.app.modules or [])
    for dt in doctypes:
        if dt.module:
            app_modules.add(dt.module)

    for mod in sorted(app_modules):
        try:
            exists = await frappe_client.module_exists(mod)
            if not exists:
                await frappe_client.create_module(mod)
                created.append(f"Module: {mod}")
                logger.info("Created missing module: %s", mod)
        except Exception as exc:
            logger.warning("Could not verify or create module '%s': %s", mod, exc)

    # ---------------------------------------------------------------
    # Step 1 — Create Roles
    # ---------------------------------------------------------------
    for role in app_roles:
        try:
            exists = await frappe_client.role_exists(role)
            if exists:
                logger.info("Role '%s' already exists — skipping.", role)
                continue
            await frappe_client.create_role(role)
            created.append(f"Role: {role}")
            logger.info("Created role: %s", role)
        except FrappeAPIError as exc:
            msg = f"Failed to create Role '{role}': {exc.detail}"
            logger.warning(msg)
            errors.append(msg)

    # ---------------------------------------------------------------
    # Step 2 — Sort DocTypes: child first, then settings, master, transaction, log
    # ---------------------------------------------------------------
    kind_order = {"child": 0, "settings": 1, "master": 2, "transaction": 3, "log": 4}
    sorted_doctypes = sorted(doctypes, key=lambda dt: kind_order.get(dt.kind.value, 5))

    # ---------------------------------------------------------------
    # Step 3 — Create DocTypes
    # ---------------------------------------------------------------
    for dt_spec in sorted_doctypes:
        try:
            exists = await frappe_client.doctype_exists(dt_spec.name)
            if exists:
                logger.info("DocType '%s' already exists — skipping.", dt_spec.name)
                continue

            wire = _doctype_to_frappe(dt_spec)
            await frappe_client.create_doctype(wire)
            created.append(f"DocType: {dt_spec.name}")
            logger.info("Created DocType: %s", dt_spec.name)

            # Build preview URL for non-child, non-settings doctypes
            if not dt_spec.istable and not dt_spec.is_single:
                preview_urls.append(f"{frappe_url}/app/{_kebab(dt_spec.name)}/new")

        except FrappeAPIError as exc:
            msg = f"Failed to create DocType '{dt_spec.name}': {exc.detail}"
            logger.error(msg)
            errors.append(msg)
        except Exception as exc:
            msg = f"Unexpected error for DocType '{dt_spec.name}': {exc}"
            logger.error(msg)
            errors.append(msg)

    # ---------------------------------------------------------------
    # Step 4 — Create Workflows
    # ---------------------------------------------------------------
    for wf_spec in workflows:
        try:
            wire = _workflow_to_frappe(wf_spec)
            await frappe_client.create_workflow(wire)
            created.append(f"Workflow: {wf_spec.name}")
            logger.info("Created Workflow: %s", wf_spec.name)
        except FrappeAPIError as exc:
            msg = f"Failed to create Workflow '{wf_spec.name}': {exc.detail}"
            logger.error(msg)
            errors.append(msg)

    # ---------------------------------------------------------------
    # Step 5 — Generate & create Server Scripts & Client Scripts
    # ---------------------------------------------------------------
    # Map doctype names to their field definitions for script context
    dt_fields_map = {dt.name: [f.model_dump() for f in dt.fields] for dt in doctypes}

    server_scripts: list[ServerScriptSpec] = spec.get_server_scripts()
    for s_spec in server_scripts:
        try:
            fields = dt_fields_map.get(s_spec.reference_doctype, [])
            code = s_spec.script
            if not code:
                try:
                    code = await script_generator.generate_script(
                        pattern=s_spec.pattern,
                        purpose=s_spec.purpose,
                        doctype_name=s_spec.reference_doctype,
                        fields=fields,
                    )
                except Exception as gen_err:
                    logger.warning("Could not generate script via LLM, using fallback template: %s", gen_err)
                    from snippets import SNIPPET_LIBRARY
                    code = SNIPPET_LIBRARY.get(s_spec.pattern, f"# {s_spec.purpose}\npass\n")

            await frappe_client.create_server_script({
                "name": s_spec.name,
                "script_type": s_spec.script_type,
                "reference_doctype": s_spec.reference_doctype,
                "doctype_event": s_spec.doctype_event,
                "script": code,
            })
            created.append(f"Server Script: {s_spec.name}")
            logger.info("Created Server Script: %s", s_spec.name)
        except Exception as exc:
            msg = f"Failed to create Server Script '{s_spec.name}': {exc}"
            logger.warning(msg)
            errors.append(msg)

    client_scripts: list[ClientScriptSpec] = spec.get_client_scripts()
    for c_spec in client_scripts:
        try:
            fields = dt_fields_map.get(c_spec.reference_doctype, [])
            code = c_spec.script
            if not code:
                try:
                    code = await script_generator.generate_client_script(
                        pattern=c_spec.pattern,
                        purpose=c_spec.purpose,
                        doctype_name=c_spec.reference_doctype,
                        fields=fields,
                    )
                except Exception as gen_err:
                    logger.warning("Could not generate client script via LLM: %s", gen_err)
                    code = f"// {c_spec.purpose}\n"

            await frappe_client.create_client_script({
                "name": c_spec.name,
                "reference_doctype": c_spec.reference_doctype,
                "script": code,
                "view": c_spec.view,
            })
            created.append(f"Client Script: {c_spec.name}")
            logger.info("Created Client Script: %s", c_spec.name)
        except Exception as exc:
            msg = f"Failed to create Client Script '{c_spec.name}': {exc}"
            logger.warning(msg)
            errors.append(msg)

    # ---------------------------------------------------------------
    # Step 6 — Reports and Dashboard
    # ---------------------------------------------------------------
    try:
        report_results = await report_builder.build_reports_and_dashboard(
            spec.app, frappe_client
        )
        for r_name in report_results.get("reports", []):
            created.append(f"Report: {r_name}")
        if report_results.get("dashboard"):
            created.append(f"Dashboard: {report_results['dashboard']}")
        for r_err in report_results.get("errors", []):
            errors.append(r_err)
    except Exception as exc:
        msg = f"Reports/Dashboard builder error: {exc}"
        logger.warning(msg)
        errors.append(msg)

    # ---------------------------------------------------------------
    # Step 7 — Seed sample data (best-effort)
    # ---------------------------------------------------------------
    for doctype_name, records in sample_data.items():
        if not isinstance(records, list):
            continue
        for record in records:
            try:
                await frappe_client.create_document(doctype_name, record)
                created.append(f"Sample {doctype_name}: {record.get('name', '?')}")
            except Exception as exc:
                msg = f"Could not seed sample {doctype_name}: {exc}"
                logger.warning(msg)
                errors.append(msg)

    # ---------------------------------------------------------------
    # Step 8 — Verification tests on created DocTypes
    # ---------------------------------------------------------------
    test_results = {}
    created_dt_names = [dt.name for dt in sorted_doctypes if not dt.istable and not dt.is_single]
    try:
        test_summary = await run_tests.run_all_tests(created_dt_names, frappe_client)
        test_results = test_summary
        logger.info(
            "DocType test summary: %d/%d passed",
            test_summary.get("passed", 0),
            test_summary.get("total", 0),
        )
    except Exception as exc:
        logger.warning("DocType testing encountered error: %s", exc)

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------
    if errors and not created:
        status = "failed"
    elif errors:
        status = "partial"
    else:
        status = "done"

    return {
        "status": status,
        "created": created,
        "errors": errors,
        "preview_urls": preview_urls,
        "tests": test_results,
    }
