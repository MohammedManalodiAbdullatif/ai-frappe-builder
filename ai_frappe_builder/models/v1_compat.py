"""
v1_compat.py — Backward-compatibility wrapper for legacy AppSpec 1.0.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from ai_frappe_builder.models.app_spec_v2 import (
    ClientScriptSpec,
    DocTypeSpec,
    ReportSpec,
    ServerScriptSpec,
    WorkflowSpec,
)


class AppSpec(BaseModel):
    """
    Legacy AppSpec 1.0 container retained for backward-compatibility.
    Internal components should preferentially use AppSpecV2.
    """

    status: Literal["ready", "needs_input", "drafting", "validating", "failed"] = "needs_input"
    spec_version: str = "1.0"
    questions: list[dict[str, Any]] = []
    assumptions: list[str] = []
    app: dict[str, Any] | None = None

    def get_doctypes(self) -> list[DocTypeSpec]:
        """Parse and return DocTypeSpec list from the raw app dict."""
        if not self.app:
            return []
        raw_doctypes = self.app.get("doctypes", [])
        default_module = (self.app.get("modules") or ["Custom"])[0]
        cleaned = []
        for dt in raw_doctypes:
            d = dict(dt)
            if "name" not in d and "doctype" in d:
                d["name"] = d["doctype"]
            elif "name" not in d and "title" in d:
                d["name"] = d["title"]
            if "module" not in d:
                d["module"] = default_module
            if "kind" not in d:
                d["kind"] = "child" if d.get("istable") else "master"
            if "autoname" not in d:
                d["autoname"] = "hash" if d.get("istable") else "Prompt"
            cleaned.append(DocTypeSpec(**d))
        return cleaned

    def get_workflows(self) -> list[WorkflowSpec]:
        """Parse and return WorkflowSpec list from the raw app dict."""
        if not self.app:
            return []
        raw_workflows = self.app.get("workflows", [])
        cleaned = []
        for wf in raw_workflows:
            w = dict(wf)
            if "document_type" not in w:
                w["document_type"] = w.get("doctype") or w.get("ref_doctype") or ""
            cleaned_states = []
            for s in w.get("states", []):
                sd = dict(s)
                if "doc_status" not in sd:
                    status_str = str(sd.get("docs", "")).lower()
                    if "cancel" in status_str:
                        sd["doc_status"] = 2
                    elif (
                        "submit" in status_str or "complete" in status_str or "active" in status_str
                    ):
                        sd["doc_status"] = 1
                    else:
                        sd["doc_status"] = 0
                if "allow_edit" not in sd:
                    sd["allow_edit"] = "System Manager"
                cleaned_states.append(sd)
            w["states"] = cleaned_states

            cleaned_transitions = []
            for t in w.get("transitions", []):
                td = dict(t)
                if "allowed" not in td and "allow_role" in td:
                    td["allowed"] = td["allow_role"]
                elif "allowed" not in td:
                    td["allowed"] = "System Manager"
                cleaned_transitions.append(td)
            w["transitions"] = cleaned_transitions

            cleaned.append(WorkflowSpec(**w))
        return cleaned

    def get_server_scripts(self) -> list[ServerScriptSpec]:
        if not self.app:
            return []
        return [ServerScriptSpec(**s) for s in self.app.get("server_scripts", [])]

    def get_client_scripts(self) -> list[ClientScriptSpec]:
        if not self.app:
            return []
        return [ClientScriptSpec(**s) for s in self.app.get("client_scripts", [])]

    def get_reports(self) -> list[ReportSpec]:
        if not self.app:
            return []
        return [ReportSpec(**r) for r in self.app.get("reports", [])]
