"""
documenter.py — Automated technical documentation synthesizer.
Generates comprehensive README, Mermaid ERD data models, workflow state diagrams,
and role-based operational user guides for exported Frappe applications.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from ai_frappe_builder.models.app_spec_v2 import AppSpecV2

logger = logging.getLogger(__name__)


class DocumentationBundle(BaseModel):
    """Set of technical documentation files generated for an exported application."""

    readme_md: str
    data_model_erd_md: str
    workflows_md: str
    user_guide_md: str


class Documenter:
    """Deterministic documentation synthesizer creating diagrams and user manuals."""

    def generate_mermaid_erd(self, spec: AppSpecV2) -> str:
        """
        Generate Mermaid ERD diagram representing all DocTypes, fields, and relationships.
        """
        if not spec.app or not spec.app.doctypes:
            return "```mermaid\nerDiagram\n    EMPTY ||--|| EMPTY : none\n```"

        lines = ["```mermaid", "erDiagram"]

        # Entity definitions
        for dt in spec.app.doctypes:
            clean_name = dt.name.replace(" ", "_")
            lines.append(f"    {clean_name} {{")
            for f in dt.fields:
                if f.fieldtype in ("Section Break", "Column Break", "Tab Break"):
                    continue
                ftype = f.fieldtype.replace(" ", "_")
                req_marker = "req" if f.reqd else "opt"
                lines.append(f"        {ftype} {f.fieldname} \"{req_marker}\"")
            lines.append("    }")

        # Relationship edges
        for dt in spec.app.doctypes:
            src = dt.name.replace(" ", "_")
            for f in dt.fields:
                if f.fieldtype == "Link" and f.options:
                    target = f.options.replace(" ", "_")
                    lines.append(f"    {src} }}o--|| {target} : \"links ({f.fieldname})\"")
                elif f.fieldtype in ("Table", "Table MultiSelect") and f.options:
                    child = f.options.replace(" ", "_")
                    lines.append(f"    {src} ||--|{{ {child} : \"contains ({f.fieldname})\"")

        lines.append("```")
        return "\n".join(lines)

    def generate_mermaid_workflows(self, spec: AppSpecV2) -> str:
        """
        Generate Mermaid stateDiagram-v2 for all approval workflows.
        """
        if not spec.app or not spec.app.workflows:
            return "No multi-state workflows configured."

        blocks = []
        for wf in spec.app.workflows:
            lines = [
                f"### {wf.name} ({wf.document_type})",
                "",
                "```mermaid",
                "stateDiagram-v2",
                "    [*] --> Draft",
            ]
            for tr in wf.transitions:
                lines.append(f"    {tr.state} --> {tr.next_state} : {tr.action} ({tr.allowed})")
            lines.append("```")
            blocks.append("\n".join(lines))

        return "\n\n".join(blocks)

    def generate_role_user_guide(self, spec: AppSpecV2) -> str:
        """
        Generate operational user guide categorized by role.
        """
        if not spec.app:
            return "No application metadata."

        app = spec.app
        lines = [
            f"# {app.title} — Role-Based User Manual",
            "",
            "This guide outlines daily operations and desk workflows for each designated system role.",
            "",
        ]

        roles = app.roles or ["System Manager"]
        for role in roles:
            lines.append(f"## Role: {role}")
            lines.append(f"Permissions and responsibilities for **{role}**:")
            lines.append("")

            # Find doctypes where this role has permissions
            matching_dts = []
            for dt in app.doctypes:
                p_rows = [p for p in dt.permissions if p.role == role]
                if p_rows:
                    matching_dts.append((dt.name, p_rows[0]))

            if matching_dts:
                lines.append("| DocType | Read | Write | Create | Delete | Submit |")
                lines.append("|---|---|---|---|---|---|")
                for dt_name, p in matching_dts:
                    r = "✓" if p.read else "✗"
                    w = "✓" if p.write else "✗"
                    c = "✓" if p.create else "✗"
                    d = "✓" if p.delete else "✗"
                    s = "✓" if getattr(p, "submit", False) else "-"
                    lines.append(f"| {dt_name} | {r} | {w} | {c} | {d} | {s} |")
            else:
                lines.append("*Desk access and standard administrative permissions.*")
            lines.append("")

        return "\n".join(lines)

    def generate_bundle(self, spec: AppSpecV2) -> DocumentationBundle:
        """Synthesize complete technical documentation suite."""
        app_title = spec.app.title if spec.app else "Frappe Application"
        app_name = spec.app.app_name if spec.app else "custom_app"
        desc = spec.app.description if spec.app else ""

        readme = f"""# {app_title}

{desc}

### Fast-Track Installation
```bash
bench get-app {app_name}
bench --site <your-site> install-app {app_name}
bench --site <your-site> migrate
```

### Documentation
- [Data Model & Schema (ERD)](docs/data-model.md)
- [Workflow Approval Lifecycles](docs/workflows.md)
- [Role-Based User Manual](docs/user-guide.md)
"""

        erd = f"# {app_title} — Data Model & Schema (ERD)\n\n" + self.generate_mermaid_erd(spec)
        workflows = f"# {app_title} — Workflows\n\n" + self.generate_mermaid_workflows(spec)
        user_guide = self.generate_role_user_guide(spec)

        return DocumentationBundle(
            readme_md=readme,
            data_model_erd_md=erd,
            workflows_md=workflows,
            user_guide_md=user_guide,
        )
