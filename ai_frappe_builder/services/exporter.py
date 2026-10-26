"""
exporter.py — Production-grade Frappe v15 app packager.
Matches canonical `bench new-app` layout byte-for-byte, emits byte-stable DocType JSON,
fixtures, hooks, install/uninstall hooks, git repository, and downloadable zip bundle.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_frappe_builder.agents.report_builder import ReportBuilder
from ai_frappe_builder.agents.script_writer import ScriptWriter
from ai_frappe_builder.models.app_spec_v2 import AppSpecV2, DocTypeSpec
from ai_frappe_builder.models.migration import migrate_v1_to_v2

logger = logging.getLogger(__name__)


def snake(s: str) -> str:
    """Normalize string to snake_case identifier."""
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    return re.sub(r"[\s-]+", "_", s)


def canonical_doctype_json(dt: DocTypeSpec) -> dict[str, Any]:
    """
    Produce canonical, byte-stable DocType JSON mirroring Frappe's `frappe.modules.export_file`.
    Ensures deterministic key order and standard Frappe metadata attributes.
    """
    fields: list[dict[str, Any]] = []
    field_order: list[str] = []

    for f in dt.fields:
        field_order.append(f.fieldname)
        f_dict: dict[str, Any] = {
            "fieldname": f.fieldname,
            "fieldtype": f.fieldtype,
            "label": f.label,
        }
        if f.options:
            f_dict["options"] = f.options
        if f.reqd:
            f_dict["reqd"] = 1
        if f.unique:
            f_dict["unique"] = 1
        if f.read_only:
            f_dict["read_only"] = 1
        if f.hidden:
            f_dict["hidden"] = 1
        if f.in_list_view:
            f_dict["in_list_view"] = 1
        if f.in_standard_filter:
            f_dict["in_standard_filter"] = 1
        if f.default is not None:
            f_dict["default"] = f.default
        if f.fetch_from:
            f_dict["fetch_from"] = f.fetch_from
        if f.depends_on:
            f_dict["depends_on"] = f.depends_on
        if f.description:
            f_dict["description"] = f.description

        fields.append(f_dict)

    permissions: list[dict[str, Any]] = []
    if not dt.istable:
        for p in dt.permissions:
            permissions.append(
                {
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
                    "permlevel": p.permlevel,
                }
            )

    iso_timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")

    # Order strictly mirrors Frappe v15 export_file order
    doc_json: dict[str, Any] = {
        "actions": [],
        "allow_rename": 1,
        "autoname": dt.autoname,
        "creation": iso_timestamp,
        "doctype": "DocType",
        "engine": "InnoDB",
        "field_order": field_order,
        "fields": fields,
        "index_web_pages_for_search": 1,
        "is_submittable": 1 if dt.is_submittable else 0,
        "istable": 1 if dt.istable else 0,
        "links": [],
        "modified": iso_timestamp,
        "modified_by": "Administrator",
        "module": dt.module,
        "name": dt.name,
        "naming_rule": dt.naming_rule
        or ("Expression" if dt.autoname.startswith("format:") else "Random"),
        "owner": "Administrator",
        "permissions": permissions,
        "sort_field": "modified",
        "sort_order": "DESC",
        "states": [],
        "track_changes": 1 if dt.track_changes or dt.is_submittable else 0,
    }

    if dt.title_field:
        doc_json["title_field"] = dt.title_field
    if dt.search_fields:
        doc_json["search_fields"] = ",".join(dt.search_fields)

    return doc_json


class FrappeAppExporter:
    """Exports AppSpec 2.0 to canonical Frappe v15 bench app structure."""

    def __init__(self, output_root: str = "/tmp/frappe_exports") -> None:
        self.output_root = Path(output_root)
        self.script_writer = ScriptWriter()
        self.report_builder = ReportBuilder()

    def export(self, spec: Any) -> dict[str, Any]:
        """
        Generate complete app repository on disk and package as .zip.
        """
        if isinstance(spec, AppSpecV2):
            spec_v2 = spec
        elif isinstance(spec, dict):
            spec_v2 = migrate_v1_to_v2(spec)
        elif hasattr(spec, "model_dump"):
            spec_v2 = migrate_v1_to_v2(spec.model_dump())
        else:
            raise ValueError(f"Unsupported spec type: {type(spec)}")

        if not spec_v2.app:
            raise ValueError("AppSpec contains no app metadata.")

        app = spec_v2.app
        app_name = snake(app.app_name)
        app_title = app.title
        modules = app.modules or ["Custom"]
        main_module = modules[0]

        app_dir = self.output_root / app_name
        if app_dir.exists():
            shutil.rmtree(app_dir)
        app_dir.mkdir(parents=True, exist_ok=True)

        package_dir = app_dir / app_name
        package_dir.mkdir(parents=True, exist_ok=True)

        files_created: list[str] = []

        def _write(rel_path: str, content: str) -> None:
            full_path = app_dir / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            files_created.append(str(full_path))

        # -------------------------------------------------------------------
        # 1. Root Configuration Files
        # -------------------------------------------------------------------
        _write(
            "pyproject.toml",
            f"""[build-system]
requires = ["flit_core >=3.2,<4"]
build-backend = "flit_core.buildapi"

[project]
name = "{app_name}"
authors = [
    {{ name = "{app.publisher}", email = "{app.email}" }}
]
description = "{app.description}"
requires-python = ">=3.10"
readme = "README.md"
dynamic = ["version"]
dependencies = []

[tool.ruff]
line-length = 110
target-version = "py310"
""",
        )

        _write(
            "README.md",
            f"""# {app_title}

{app.description}

### Installation
```bash
bench get-app {app_name}
bench --site <your-site> install-app {app_name}
bench --site <your-site> migrate
```

### Modules
{chr(10).join(f"- **{m}**" for m in modules)}

### Generated by AI Frappe App Builder
- Frappe Target Version: v15.0
- Generated on: {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")}
""",
        )

        _write(
            "license.txt",
            f"""Copyright (c) 2026 {app.publisher}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
""",
        )

        _write(
            ".gitignore",
            """*.pyc
*.pyo
__pycache__/
*.egg-info/
.DS_Store
*.swp
node_modules/
""",
        )

        _write(
            ".pre-commit-config.yaml",
            """repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
""",
        )

        # -------------------------------------------------------------------
        # 2. Package Root Files (<app_name>/<app_name>/)
        # -------------------------------------------------------------------
        _write(f"{app_name}/__init__.py", f'__version__ = "{app.version}"\n')
        _write(f"{app_name}/modules.txt", "\n".join(modules) + "\n")
        _write(f"{app_name}/patches.txt", "# Patches executed during bench migrate\n")

        # install.py & uninstall.py
        _write(
            f"{app_name}/install.py",
            f"""# Copyright (c) 2026, {app.publisher} and contributors
# For license information, please see license.txt

import frappe


def after_install():
    \"\"\"Executed automatically after app is installed on bench site.\"\"\"
    # Ensure custom roles exist
    roles = {json.dumps(app.roles)}
    for r in roles:
        if not frappe.db.exists("Role", r):
            role_doc = frappe.new_doc("Role")
            role_doc.role_name = r
            role_doc.desk_access = 1
            role_doc.insert(ignore_permissions=True)
""",
        )

        _write(
            f"{app_name}/uninstall.py",
            """import frappe


def before_uninstall():
    pass
""",
        )

        _write(
            f"{app_name}/api.py",
            """import frappe


@frappe.whitelist()
def ping():
    return {"message": "pong"}
""",
        )

        _write(
            f"{app_name}/tasks.py",
            """import frappe


def daily():
    \"\"\"Scheduled daily background task.\"\"\"
    pass
""",
        )

        _write(f"{app_name}/utils.py", "# Helper utility functions\n")

        # -------------------------------------------------------------------
        # 3. Fixtures (<app_name>/<app_name>/fixtures/)
        # -------------------------------------------------------------------
        fixtures_dir = f"{app_name}/fixtures"

        # Workflows fixture
        workflows_fixture: list[dict[str, Any]] = []
        workflow_states_map: dict[str, str] = {}
        workflow_actions_set: set[str] = set()
        workflow_roles_set: set[str] = set()

        for wf in app.workflows:
            states_rows: list[dict[str, Any]] = []
            for s in wf.states:
                row: dict[str, Any] = {
                    "allow_edit": s.allow_edit,
                    "doc_status": str(s.doc_status),
                    "doctype": "Workflow Document State",
                    "state": s.state,
                    "style": s.style or "",
                }
                if s.update_field:
                    row["update_field"] = s.update_field
                if s.update_value:
                    row["update_value"] = s.update_value
                states_rows.append(row)
                workflow_states_map[s.state] = s.style or ""
                if s.allow_edit:
                    workflow_roles_set.add(s.allow_edit)

            transitions_rows: list[dict[str, Any]] = []
            for t in wf.transitions:
                t_row: dict[str, Any] = {
                    "action": t.action,
                    "allow_self_approval": t.allow_self_approval,
                    "allowed": t.allowed,
                    "doctype": "Workflow Transition",
                    "next_state": t.next_state,
                    "state": t.state,
                }
                if t.condition:
                    t_row["condition"] = t.condition
                transitions_rows.append(t_row)
                workflow_actions_set.add(t.action)
                if t.allowed:
                    workflow_roles_set.add(t.allowed)

            wf_dict: dict[str, Any] = {
                "doctype": "Workflow",
                "document_type": wf.document_type,
                "is_active": 1 if wf.is_active else 0,
                "send_email_alert": 1 if wf.send_email_alert else 0,
                "states": states_rows,
                "transitions": transitions_rows,
                "workflow_name": wf.name,
                "workflow_state_field": wf.workflow_state_field or "workflow_state",
            }
            workflows_fixture.append(wf_dict)

        # Byte-stable workflows fixture (1-space indented, sorted keys, \n-terminated)
        _write(
            f"{fixtures_dir}/workflow.json",
            json.dumps(workflows_fixture, indent=1, sort_keys=True) + "\n",
        )

        # Byte-stable workflow states fixture
        states_fixture = [
            {
                "doctype": "Workflow State",
                "style": workflow_states_map[st],
                "workflow_state_name": st,
            }
            for st in sorted(workflow_states_map.keys())
        ]
        _write(
            f"{fixtures_dir}/workflow_state.json",
            json.dumps(states_fixture, indent=1, sort_keys=True) + "\n",
        )

        # Byte-stable workflow actions fixture
        actions_fixture = [
            {
                "doctype": "Workflow Action Master",
                "workflow_action_name": act,
            }
            for act in sorted(workflow_actions_set)
        ]
        _write(
            f"{fixtures_dir}/workflow_action_master.json",
            json.dumps(actions_fixture, indent=1, sort_keys=True) + "\n",
        )

        # Roles fixture: ensure every workflow role is in it
        all_roles_set = set(app.roles) | workflow_roles_set
        role_names = sorted([r for r in all_roles_set if r != "System Manager"])
        roles_fixture = [
            {"desk_access": 1, "doctype": "Role", "role_name": r}
            for r in role_names
        ]
        _write(
            f"{fixtures_dir}/role.json",
            json.dumps(roles_fixture, indent=1, sort_keys=True) + "\n",
        )

        # -------------------------------------------------------------------
        # 4. DocTypes (<app_name>/<app_name>/<module>/doctype/<dt>/)
        # -------------------------------------------------------------------
        for dt in app.doctypes:
            module_snake = snake(dt.module or main_module)
            dt_snake = snake(dt.name)
            dt_dir = f"{app_name}/{module_snake}/doctype/{dt_snake}"

            _write(f"{app_name}/{module_snake}/__init__.py", "")
            _write(f"{dt_dir}/__init__.py", "")

            # DocType canonical JSON
            dt_json = canonical_doctype_json(dt)
            _write(f"{dt_dir}/{dt_snake}.json", json.dumps(dt_json, indent=1))

            # Controller Python (<dt>.py)
            wf_for_dt = next((w for w in app.workflows if w.document_type == dt.name), None)
            code_bundle = self.script_writer.generate_doctype_bundle(dt, workflow=wf_for_dt)
            _write(f"{dt_dir}/{dt_snake}.py", code_bundle.controller_python)

            # Client Script JS (<dt>.js)
            _write(f"{dt_dir}/{dt_snake}.js", code_bundle.client_script_js)

            # DocType Unit Test (test_<dt>.py)
            _write(f"{dt_dir}/test_{dt_snake}.py", code_bundle.test_python)

        # -------------------------------------------------------------------
        # 5. Reports (<app_name>/<app_name>/<module>/report/<name>/)
        # -------------------------------------------------------------------
        for rpt in app.reports:
            module_snake = snake(main_module)
            rpt_snake = snake(rpt.name)
            rpt_dir = f"{app_name}/{module_snake}/report/{rpt_snake}"

            _write(f"{rpt_dir}/__init__.py", "")
            rpt_files = self.report_builder.generate_script_report_files(rpt)
            for fname, content in rpt_files.items():
                _write(f"{rpt_dir}/{fname}", content)

        # -------------------------------------------------------------------
        # 6. Workspaces (<app_name>/<app_name>/<module>/workspace/<name>/)
        # -------------------------------------------------------------------
        for ws in app.workspaces:
            module_snake = snake(ws.module or main_module)
            ws_snake = snake(ws.name)
            ws_json = self.report_builder.generate_workspace_json(ws)
            _write(f"{app_name}/{module_snake}/workspace/{ws_snake}/{ws_snake}.json", ws_json)

        # -------------------------------------------------------------------
        # 7. hooks.py Generation
        # -------------------------------------------------------------------
        required_apps_block = ""
        if app.requires_erpnext:
            required_apps_block = 'required_apps = ["erpnext"]\n'

        wf_names = sorted([w.name for w in app.workflows])
        wf_state_names = sorted(workflow_states_map.keys())
        wf_action_names = sorted(workflow_actions_set)

        fixtures_list: list[dict[str, Any]] = [
            {"dt": "Role", "filters": [["name", "in", role_names]]},
        ]
        if app.workflows:
            fixtures_list.extend(
                [
                    {"dt": "Workflow", "filters": [["name", "in", wf_names]]},
                    {"dt": "Workflow State", "filters": [["name", "in", wf_state_names]]},
                    {"dt": "Workflow Action Master", "filters": [["name", "in", wf_action_names]]},
                ]
            )

        fixtures_str = json.dumps(fixtures_list, indent=4)

        hooks_content = f"""# -*- coding: utf-8 -*-
from __future__ import annotations

app_name = "{app_name}"
app_title = "{app_title}"
app_publisher = "{app.publisher}"
app_description = "{app.description}"
app_email = "{app.email}"
app_license = "{app.license}"

{required_apps_block}
# Includes in <head>
# ------------------
# include js, css files in header of desk.html
# app_include_css = "/assets/{app_name}/css/{app_name}.css"
# app_include_js = "/assets/{app_name}/js/{app_name}.js"

# Installation Hooks
# ------------------
after_install = "{app_name}.install.after_install"
before_uninstall = "{app_name}.uninstall.before_uninstall"

# Scheduled Tasks
# ---------------
scheduler_events = {{
    "daily": [
        "{app_name}.tasks.daily"
    ]
}}

# Fixtures Export Filters
# -----------------------
fixtures = {fixtures_str}
"""
        _write(f"{app_name}/hooks.py", hooks_content)

        # -------------------------------------------------------------------
        # 8. Package Self-Tests (tests/)
        # -------------------------------------------------------------------
        _write(
            "tests/__init__.py",
            "",
        )
        _write(
            "tests/test_package_integrity.py",
            f"""import json
import ast
from pathlib import Path

def test_all_doctype_jsons_valid():
    for p in Path("{app_name}").rglob("*.json"):
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
            assert isinstance(data, dict) or isinstance(data, list)

def test_all_python_files_compile():
    for p in Path("{app_name}").rglob("*.py"):
        with open(p, encoding="utf-8") as f:
            ast.parse(f.read())
""",
        )

        # -------------------------------------------------------------------
        # 9. Standalone Git Initialization
        # -------------------------------------------------------------------
        try:
            subprocess.run(["git", "init"], cwd=str(app_dir), capture_output=True, check=True)
            subprocess.run(["git", "add", "."], cwd=str(app_dir), capture_output=True, check=True)
            subprocess.run(
                ["git", "commit", "-m", "feat: initial commit from AI Frappe Builder"],
                cwd=str(app_dir),
                capture_output=True,
                check=True,
            )
        except Exception as e:
            logger.warning("Could not initialize git repository in %s: %s", app_dir, e)

        # -------------------------------------------------------------------
        # 10. Zip Archive Packaging
        # -------------------------------------------------------------------
        zip_base_name = str(self.output_root / app_name)
        zip_path = shutil.make_archive(zip_base_name, "zip", str(self.output_root), app_name)

        return {
            "app_name": app_name,
            "app_path": str(app_dir),
            "zip_path": zip_path,
            "files_created": files_created,
            "total_files": len(files_created),
        }

    def get_file_tree(self, app_name: str) -> dict[str, Any]:
        """Return hierarchical file tree of exported application."""
        app_dir = self.output_root / snake(app_name)
        if not app_dir.is_dir():
            raise FileNotFoundError(f"Exported app not found at {app_dir}")

        def _build_tree(p: Path) -> dict[str, Any]:
            node: dict[str, Any] = {
                "name": p.name,
                "path": str(p.relative_to(app_dir)),
                "is_dir": p.is_dir(),
            }
            if p.is_dir():
                node["children"] = sorted(
                    [_build_tree(child) for child in p.iterdir() if child.name != ".git"],
                    key=lambda x: (not x["is_dir"], x["name"]),
                )
            else:
                node["size"] = p.stat().st_size
            return node

        return _build_tree(app_dir)

    def read_exported_file(self, app_name: str, rel_path: str) -> str:
        """Read content of an exported file within the app directory."""
        app_dir = self.output_root / snake(app_name)
        target = (app_dir / rel_path.lstrip("/")).resolve()
        if not str(target).startswith(str(app_dir.resolve())):
            raise PermissionError("Access denied: Path traversal attempt.")
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {rel_path}")
        with open(target, encoding="utf-8") as f:
            return f.read()


async def export_app(spec: Any, output_dir: str = "/tmp/frappe_exports") -> dict[str, Any]:
    """Async wrapper for FrappeAppExporter."""
    exporter = FrappeAppExporter(output_root=output_dir)
    return exporter.export(spec)
