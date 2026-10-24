"""
models.py — Pydantic v2 data models for the AI Frappe App Builder.

Covers the full App Spec schema that the LLM planner produces and the
applier consumes to create DocTypes, Workflows, etc. on a Frappe site.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class FrappeFieldType(str, Enum):
    """All 33 Frappe field types (as of Frappe v15)."""

    ATTACH = "Attach"
    ATTACH_IMAGE = "Attach Image"
    BARCODE = "Barcode"
    BUTTON = "Button"
    CHECK = "Check"
    CODE = "Code"
    COLOR = "Color"
    COLUMN_BREAK = "Column Break"
    CURRENCY = "Currency"
    DATA = "Data"
    DATE = "Date"
    DATETIME = "Datetime"
    DURATION = "Duration"
    DYNAMIC_LINK = "Dynamic Link"
    FLOAT = "Float"
    FOLD = "Fold"
    GEOLOCATION = "Geolocation"
    HEADING = "Heading"
    HTML = "HTML"
    HTML_EDITOR = "HTML Editor"
    ICON = "Icon"
    IMAGE = "Image"
    INT = "Int"
    JSON = "JSON"
    LINK = "Link"
    LONG_TEXT = "Long Text"
    MARKDOWN_EDITOR = "Markdown Editor"
    PASSWORD = "Password"
    PERCENT = "Percent"
    PHONE = "Phone"
    READ_ONLY = "Read Only"
    RATING = "Rating"
    SECTION_BREAK = "Section Break"
    SELECT = "Select"
    SIGNATURE = "Signature"
    SMALL_TEXT = "Small Text"
    TABLE = "Table"
    TABLE_MULTISELECT = "Table MultiSelect"
    TAB_BREAK = "Tab Break"
    TEXT = "Text"
    TEXT_EDITOR = "Text Editor"
    TIME = "Time"


# ---------------------------------------------------------------------------
# Field-level spec
# ---------------------------------------------------------------------------


class FieldSpec(BaseModel):
    """Specification for a single DocType field."""

    fieldname: str = Field(..., description="snake_case identifier")
    label: str = Field(..., description="Human-readable label shown in the UI")
    fieldtype: str = Field(..., description="Frappe field type string")
    options: Optional[str] = Field(
        None,
        description=(
            "For Link: target DocType. For Table: child DocType. "
            "For Select: newline-separated values."
        ),
    )
    reqd: bool = False
    unique: bool = False
    read_only: bool = False
    hidden: bool = False
    in_list_view: bool = False
    in_standard_filter: bool = False
    default: Optional[str] = None
    fetch_from: Optional[str] = None
    depends_on: Optional[str] = None

    @field_validator("fieldname")
    @classmethod
    def fieldname_snake_case(cls, v: str) -> str:
        if " " in v:
            raise ValueError(f"fieldname must be snake_case, got: {v!r}")
        return v.lower()


# ---------------------------------------------------------------------------
# Permission spec
# ---------------------------------------------------------------------------


class PermissionSpec(BaseModel):
    """Role-level permissions row for a DocType."""

    role: str
    read: bool = True
    write: bool = False
    create: bool = False
    delete: bool = False
    submit: bool = False
    cancel: bool = False
    amend: bool = False
    report: bool = False
    export: bool = False
    import_: bool = Field(False, alias="import")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# DocType spec
# ---------------------------------------------------------------------------


class DocTypeKind(str, Enum):
    MASTER = "master"
    TRANSACTION = "transaction"
    CHILD = "child"
    SETTINGS = "settings"
    LOG = "log"


class DocTypeSpec(BaseModel):
    """Full specification for one Frappe DocType."""

    name: str = Field(..., description="Title Case singular name, e.g. 'Rental Agreement'")
    module: str = "Custom"
    kind: DocTypeKind = DocTypeKind.MASTER
    istable: bool = False
    is_submittable: bool = False
    is_single: bool = False
    track_changes: bool = False
    autoname: str = Field("Prompt", description="naming_series: RA-.YYYY.-.##### | field:fieldname | hash")
    naming_series_options: Optional[str] = None
    title_field: Optional[str] = None
    fields: list[FieldSpec] = []
    permissions: list[PermissionSpec] = []

    @field_validator("name")
    @classmethod
    def name_title_case(cls, v: str) -> str:
        words = v.split()
        if not words:
            raise ValueError("DocType name cannot be empty")
        # Each word must start with uppercase
        for word in words:
            if word and not word[0].isupper():
                raise ValueError(
                    f"DocType name must be Title Case. Got: {v!r}"
                )
        return v


# ---------------------------------------------------------------------------
# Workflow spec
# ---------------------------------------------------------------------------


class WorkflowState(BaseModel):
    """Single state in a Frappe Workflow."""

    state: str
    doc_status: int = Field(0, ge=0, le=2, description="0=Draft, 1=Submitted, 2=Cancelled")
    allow_edit: str = Field("System Manager", description="Role allowed to edit in this state")
    is_optional_state: bool = False


class WorkflowTransition(BaseModel):
    """Edge between two workflow states."""

    state: str = Field(..., description="Source state")
    action: str = Field(..., description="Button label / action name")
    next_state: str = Field(..., description="Target state after action")
    allowed: str = Field("System Manager", alias="allow_role", description="Role allowed to trigger this transition")
    condition: Optional[str] = None

    model_config = {"populate_by_name": True}


class WorkflowSpec(BaseModel):
    """Full Frappe Workflow definition."""

    name: str
    document_type: str = Field(..., alias="doctype")
    workflow_state_field: str = "workflow_state"
    is_active: bool = True
    send_email_alert: bool = False
    states: list[WorkflowState]
    transitions: list[WorkflowTransition]

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Script & Report specs
# ---------------------------------------------------------------------------


class ServerScriptSpec(BaseModel):
    """Specification for a Frappe Server Script."""

    name: str
    script_type: str = "DocType Event"
    reference_doctype: str
    doctype_event: str = "Before Save"
    purpose: str
    pattern: str = "custom"  # one of snippet library patterns
    script: Optional[str] = None


class ClientScriptSpec(BaseModel):
    """Specification for a Frappe Client Script (JavaScript)."""

    name: str
    reference_doctype: str
    pattern: str = "set_query_filter"
    purpose: str
    script: Optional[str] = None
    view: str = "Form"


class ReportSpec(BaseModel):
    """Specification for a Frappe Script/Query Report."""

    name: str
    ref_doctype: str
    report_type: str = "Script Report"
    columns: list[dict[str, Any]] = []
    filters: list[dict[str, Any]] = []
    script: Optional[str] = None
    query: Optional[str] = None


# ---------------------------------------------------------------------------
# Top-level App Spec
# ---------------------------------------------------------------------------


class AppSpec(BaseModel):
    """
    The top-level document produced by the LLM planner.

    When status == 'needs_input', the planner wants more information before
    generating the full spec.  When status == 'ready', the full app object
    is present and ready for validation + apply.
    """

    status: Literal["ready", "needs_input"]
    spec_version: str = "1.0"
    questions: list[dict[str, Any]] = []
    assumptions: list[str] = []
    app: Optional[dict[str, Any]] = None

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
            # Clean states
            cleaned_states = []
            for s in w.get("states", []):
                sd = dict(s)
                if "doc_status" not in sd:
                    status_str = str(sd.get("docs", "")).lower()
                    if "cancel" in status_str:
                        sd["doc_status"] = 2
                    elif "submit" in status_str or "complete" in status_str or "active" in status_str:
                        sd["doc_status"] = 1
                    else:
                        sd["doc_status"] = 0
                if "allow_edit" not in sd:
                    sd["allow_edit"] = "System Manager"
                cleaned_states.append(sd)
            w["states"] = cleaned_states

            # Clean transitions
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
        """Parse and return ServerScriptSpec list from the raw app dict."""
        if not self.app:
            return []
        raw_scripts = self.app.get("server_scripts", [])
        return [ServerScriptSpec(**s) for s in raw_scripts]

    def get_client_scripts(self) -> list[ClientScriptSpec]:
        """Parse and return ClientScriptSpec list from the raw app dict."""
        if not self.app:
            return []
        raw_scripts = self.app.get("client_scripts", [])
        return [ClientScriptSpec(**s) for s in raw_scripts]

    def get_reports(self) -> list[ReportSpec]:
        """Parse and return ReportSpec list from the raw app dict."""
        if not self.app:
            return []
        raw_reports = self.app.get("reports", [])
        return [ReportSpec(**r) for r in raw_reports]


# ---------------------------------------------------------------------------
# Request / Response models for the API
# ---------------------------------------------------------------------------


class ChatStartRequest(BaseModel):
    message: str
    client_name: str = "Frappe Client"
    frappe_url: str = ""
    frappe_api_key: str = ""
    frappe_api_secret: str = ""


class ChatMessageRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    status: str
    questions: list[dict[str, Any]] = []
    assumptions: list[str] = []
    spec: Optional[dict[str, Any]] = None


class PlanResponse(BaseModel):
    spec: Optional[dict[str, Any]]
    validation: dict[str, Any]
    assumptions: list[str] = []


class ApplyResponse(BaseModel):
    status: str
    created: list[str] = []
    errors: list[str] = []
    preview_urls: list[str] = []
