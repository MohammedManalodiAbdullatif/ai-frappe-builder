"""
app_spec_v2.py — Authoritative Pydantic v2 data models for AppSpec 2.0.
Single source of truth for schema generation, validation, materialisation, and export.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Field Types Enumeration (Frappe v15)
# ---------------------------------------------------------------------------


class FrappeFieldType(StrEnum):
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
# Field Specification
# ---------------------------------------------------------------------------


class FieldSpec(BaseModel):
    """Specification for a single DocType field."""

    fieldname: str = Field(..., description="snake_case identifier")
    label: str = Field(..., description="Human-readable label shown in Desk UI")
    fieldtype: str = Field(..., description="Frappe field type string")
    options: str | None = Field(
        None,
        description=(
            "For Link: target DocType. For Table: child DocType with istable=1. "
            "For Select: newline-separated values. For Dynamic Link: fieldname of doctype."
        ),
    )
    reqd: bool = False
    unique: bool = False
    read_only: bool = False
    hidden: bool = False
    in_list_view: bool = False
    in_standard_filter: bool = False
    in_global_search: bool = False
    bold: bool = False
    allow_in_quick_entry: bool = False
    default: str | None = None
    fetch_from: str | None = None
    depends_on: str | None = None
    mandatory_depends_on: str | None = None
    read_only_depends_on: str | None = None
    description: str | None = None
    precision: int | None = None

    @field_validator("fieldname")
    @classmethod
    def fieldname_snake_case(cls, v: str) -> str:
        s = v.strip().lower()
        if not re.match(r"^[a-z][a-z0-9_]*$", s):
            # Allow layout break fieldnames if auto-generated
            if s.startswith(("section_break_", "column_break_", "tab_break_")):
                return s
            raise ValueError(
                f"fieldname must be lowercase snake_case starting with a letter, got: {v!r}"
            )
        return s


# ---------------------------------------------------------------------------
# Permission Specification
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
    share: bool = False
    print: bool = False
    email: bool = False
    permlevel: int = 0

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# DocType Specification
# ---------------------------------------------------------------------------


class DocTypeKind(StrEnum):
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
    autoname: str = Field(
        "Prompt",
        description="naming_series: RA-.YYYY.-.##### | field:fieldname | hash | autoincrement | Prompt",
    )
    naming_rule: str | None = None
    naming_series_options: str | None = None
    title_field: str | None = None
    search_fields: list[str] = Field(default_factory=list)
    description: str | None = None
    fields: list[FieldSpec] = Field(default_factory=list)
    permissions: list[PermissionSpec] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def name_title_case(cls, v: str) -> str:
        v = v.strip()
        words = v.split()
        if not words:
            raise ValueError("DocType name cannot be empty")
        for word in words:
            if word and not word[0].isupper():
                raise ValueError(f"DocType name must be Title Case. Got: {v!r}")
        return v


# ---------------------------------------------------------------------------
# Workflow Specification
# ---------------------------------------------------------------------------


class WorkflowState(BaseModel):
    """Single state in a Frappe Workflow."""

    state: str
    doc_status: int = Field(0, ge=0, le=2, description="0=Draft, 1=Submitted, 2=Cancelled")
    allow_edit: str = Field("System Manager", description="Role allowed to edit in this state")
    is_optional_state: bool = False


class WorkflowTransition(BaseModel):
    """Transition edge between two workflow states."""

    state: str = Field(..., description="Source state")
    action: str = Field(..., description="Action trigger button label")
    next_state: str = Field(..., description="Target state")
    allowed: str = Field(
        "System Manager", alias="allow_role", description="Role allowed to trigger transition"
    )
    condition: str | None = None

    model_config = {"populate_by_name": True}


class WorkflowSpec(BaseModel):
    """Full Frappe Workflow definition."""

    name: str
    document_type: str = Field(..., alias="doctype")
    workflow_state_field: str = "workflow_state"
    is_active: bool = True
    send_email_alert: bool = False
    states: list[WorkflowState] = Field(default_factory=list)
    transitions: list[WorkflowTransition] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Script & Code Specifications
# ---------------------------------------------------------------------------


class ServerScriptSpec(BaseModel):
    """Specification for a Frappe Server Script / Controller Hook."""

    name: str = "custom_server_script"
    script_type: str = "DocType Event"
    reference_doctype: str = Field("", alias="doctype")
    doctype_event: str = "Before Save"
    purpose: str = "Custom logic"
    pattern: str = "custom"
    script: str | None = None

    model_config = {"populate_by_name": True, "extra": "ignore"}


class ClientScriptSpec(BaseModel):
    """Specification for a Frappe Desk Client Script (JavaScript)."""

    name: str = "custom_client_script"
    reference_doctype: str = Field("", alias="doctype")
    view: str = "Form"
    purpose: str = "UI enhancement"
    pattern: str = "custom"
    script: str | None = None

    model_config = {"populate_by_name": True, "extra": "ignore"}


# ---------------------------------------------------------------------------
# Reporting & Analytics Specifications
# ---------------------------------------------------------------------------


class ReportSpec(BaseModel):
    """Specification for a Frappe Script or Query Report."""

    name: str = "custom_report"
    ref_doctype: str = Field("", alias="reference_doctype")
    report_type: str = "Script Report"
    columns: list[dict[str, Any]] = Field(default_factory=list)
    filters: list[dict[str, Any]] = Field(default_factory=list)
    script: str | None = None
    query: str | None = None

    model_config = {"populate_by_name": True, "extra": "ignore"}


class NumberCardSpec(BaseModel):
    """Specification for a Desk Metric Number Card."""

    name: str
    label: str
    document_type: str
    function: str = "Count"  # Count, Sum, Average, Minimum, Maximum
    aggregate_function_based_on: str | None = None
    filters_json: str = "[]"


class DashboardChartSpec(BaseModel):
    """Specification for a Desk Dashboard Chart."""

    chart_name: str
    chart_type: str = "Bar"  # Bar, Line, Pie, Percentage, Donut
    document_type: str
    based_on: str | None = None
    value_based_on: str | None = None
    group_by_type: str = "Count"


# ---------------------------------------------------------------------------
# Workspace Specification
# ---------------------------------------------------------------------------


class WorkspaceShortcut(BaseModel):
    """Shortcut item on a Frappe Workspace."""

    label: str
    type: str = "DocType"
    link_to: str


class WorkspaceLink(BaseModel):
    """Sidebar / group navigation link on a Frappe Workspace."""

    label: str
    link_to: str
    link_type: str = "DocType"


class WorkspaceSpec(BaseModel):
    """Frappe Desk Module Workspace."""

    name: str
    module: str
    label: str
    title: str
    icon: str = "package"
    shortcuts: list[WorkspaceShortcut] = Field(default_factory=list)
    links: list[WorkspaceLink] = Field(default_factory=list)
    charts: list[str] = Field(default_factory=list)
    number_cards: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# App Metadata Specification
# ---------------------------------------------------------------------------


class AppMetadata(BaseModel):
    """Complete installable app package definition."""

    app_name: str = Field(..., description="snake_case app directory name, e.g. 'car_rental'")
    title: str = Field(..., description="Human-readable title, e.g. 'Car Rental'")
    description: str = "Custom Frappe application generated with AI Frappe Builder"
    publisher: str = "Frappe Builder"
    email: str = "developer@example.com"
    license: str = "MIT"
    version: str = "0.0.1"
    frappe_version: str = "15.0.0"
    requires_erpnext: bool = False
    modules: list[str] = Field(default_factory=lambda: ["Custom"])
    roles: list[str] = Field(default_factory=list)
    doctypes: list[DocTypeSpec] = Field(default_factory=list)
    workflows: list[WorkflowSpec] = Field(default_factory=list)
    server_scripts: list[ServerScriptSpec] = Field(default_factory=list)
    client_scripts: list[ClientScriptSpec] = Field(default_factory=list)
    reports: list[ReportSpec] = Field(default_factory=list)
    number_cards: list[NumberCardSpec] = Field(default_factory=list)
    dashboard_charts: list[DashboardChartSpec] = Field(default_factory=list)
    workspaces: list[WorkspaceSpec] = Field(default_factory=list)

    @field_validator("app_name")
    @classmethod
    def app_name_snake_case(cls, v: str) -> str:
        s = v.strip().lower().replace("-", "_")
        if not re.match(r"^[a-z][a-z0-9_]*$", s):
            raise ValueError(f"app_name must be lowercase snake_case, got: {v!r}")
        return s


# ---------------------------------------------------------------------------
# Discovery & Question Models
# ---------------------------------------------------------------------------


class QuestionOption(BaseModel):
    """An interactive selectable option presented to the user during discovery."""

    label: str
    value: str
    description: str | None = None


class InterviewQuestion(BaseModel):
    """A single discovery question crafted by the Interviewer agent."""

    id: str = Field(..., description="Stable question key, e.g. 'q_b2b_vs_b2c'")
    question: str
    reason: str | None = None
    options: list[QuestionOption] = Field(default_factory=list)
    allows_custom: bool = True


# ---------------------------------------------------------------------------
# Top-Level AppSpec 2.0 Contract
# ---------------------------------------------------------------------------


class AppSpecV2(BaseModel):
    """
    Central contract and single source of truth for the generation pipeline.
    """

    spec_version: Literal["2.0"] = "2.0"
    status: Literal["ready", "needs_input", "drafting", "validating", "failed"] = "needs_input"
    archetype: str | None = None
    questions: list[InterviewQuestion] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    app: AppMetadata | None = None

    def get_doctypes(self) -> list[DocTypeSpec]:
        return self.app.doctypes if self.app else []

    def get_workflows(self) -> list[WorkflowSpec]:
        return self.app.workflows if self.app else []

    def get_server_scripts(self) -> list[ServerScriptSpec]:
        return self.app.server_scripts if self.app else []

    def get_client_scripts(self) -> list[ClientScriptSpec]:
        return self.app.client_scripts if self.app else []

    def get_reports(self) -> list[ReportSpec]:
        return self.app.reports if self.app else []

    def get_workspaces(self) -> list[WorkspaceSpec]:
        return self.app.workspaces if self.app else []
