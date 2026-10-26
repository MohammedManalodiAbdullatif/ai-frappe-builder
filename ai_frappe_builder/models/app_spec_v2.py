"""
app_spec_v2.py — Authoritative Pydantic v2 data models for AppSpec 2.0.
Single source of truth for schema generation, validation, materialisation, and export.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    allow_on_submit: bool = False
    description: str | None = None
    precision: int | None = None

    @field_validator("fieldname", mode="before")
    @classmethod
    def fieldname_snake_case(cls, v: Any) -> str:
        s = str(v).strip().lower()
        if s.startswith(("section_break_", "column_break_", "tab_break_")):
            return s
        s = re.sub(r"[\s-]+", "_", s)
        s = re.sub(r"[^a-z0-9_]", "", s)
        if not s or not s[0].isalpha():
            s = f"f_{s}" if s else "custom_field"
        return s

    @field_validator("fieldtype", mode="before")
    @classmethod
    def coerce_fieldtype(cls, v: Any) -> str:
        s = str(v).strip()
        type_map = {
            "str": "Data", "string": "Data", "varchar": "Data", "text_field": "Data",
            "int": "Int", "integer": "Int", "number": "Int",
            "bool": "Check", "boolean": "Check",
            "float": "Float", "decimal": "Float", "double": "Float",
            "datetime": "Datetime", "timestamp": "Datetime",
            "date": "Date",
            "time": "Time",
            "link": "Link", "reference": "Link",
            "table": "Table", "child_table": "Table",
            "select": "Select", "dropdown": "Select",
            "currency": "Currency", "money": "Currency",
            "percent": "Percent", "percentage": "Percent",
            "text": "Text", "long_text": "Long Text", "small_text": "Small Text",
            "text_editor": "Text Editor", "html": "HTML", "code": "Code",
            "attach": "Attach", "attachment": "Attach", "file": "Attach",
            "attach_image": "Attach Image", "image": "Image",
            "signature": "Signature", "rating": "Rating", "barcode": "Barcode",
            "section_break": "Section Break", "column_break": "Column Break", "tab_break": "Tab Break"
        }
        lower = s.lower().replace(" ", "_")
        if lower in type_map:
            return type_map[lower]
        for ft in FrappeFieldType:
            if ft.value.lower() == s.lower():
                return ft.value
        return s or "Data"


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

    @field_validator("role", mode="before")
    @classmethod
    def coerce_role(cls, v: Any) -> str:
        if isinstance(v, dict):
            return str(v.get("role") or v.get("name") or v.get("label") or "System Manager")
        return str(v).strip() if v else "System Manager"


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

    @model_validator(mode="before")
    @classmethod
    def normalize_doctype_spec(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)

        # 1. Normalize name to Title Case
        raw_name = d.get("name", "Custom DocType")
        s = re.sub(r"[_\-]+", " ", str(raw_name).strip())
        words = [w.capitalize() for w in s.split() if w]
        d["name"] = " ".join(words) or "Custom DocType"

        # 2. Kind & istable synchronization
        raw_kind = str(d.get("kind", "")).lower()
        if raw_kind == "child" or d.get("istable"):
            d["kind"] = DocTypeKind.CHILD
            d["istable"] = True
            if not d.get("autoname") or d.get("autoname") == "Prompt":
                d["autoname"] = "hash"
            d["permissions"] = []
        else:
            if d.get("kind") not in [k.value for k in DocTypeKind]:
                d["kind"] = DocTypeKind.MASTER

        # 3. Default permissions if empty and not child
        if not d.get("istable") and not d.get("permissions"):
            d["permissions"] = [
                {"role": "System Manager", "read": True, "write": True, "create": True, "delete": True}
            ]

        return d

    @field_validator("name")
    @classmethod
    def name_title_case(cls, v: str) -> str:
        s = re.sub(r"[_\-]+", " ", str(v).strip())
        words = [w.capitalize() for w in s.split() if w]
        return " ".join(words) or "Custom DocType"


# ---------------------------------------------------------------------------
# Workflow Specification
# ---------------------------------------------------------------------------

WorkflowStyle = Literal["Success", "Warning", "Danger", "Primary", ""]
WorkflowDocStatus = Literal[0, 1, 2]


class WorkflowState(BaseModel):
    """Single state in a Frappe Workflow."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    state: str = Field(..., description="Unique state identifier, e.g. Draft, Approved")
    doc_status: WorkflowDocStatus = Field(0, description="0=Draft, 1=Submitted, 2=Cancelled")
    style: WorkflowStyle = Field("", description="Frappe badge style (Success, Warning, Danger, Primary, or empty)")
    allow_edit: str = Field("System Manager", description="Role allowed to edit in this state")
    update_field: str | None = Field(None, description="Optional DocType fieldname to update on entering state")
    update_value: str | None = Field(None, description="Value to set in update_field on entering state")
    is_optional_state: bool = False

    @field_validator("allow_edit", mode="before")
    @classmethod
    def coerce_allow_edit(cls, v: Any) -> str:
        if isinstance(v, dict):
            return str(v.get("role") or v.get("name") or "System Manager")
        return str(v).strip() if v else "System Manager"

    @field_validator("doc_status", mode="before")
    @classmethod
    def coerce_doc_status(cls, v: Any) -> int:
        try:
            return int(v) if v is not None else 0
        except (ValueError, TypeError):
            return 0

    @field_validator("style", mode="before")
    @classmethod
    def coerce_style(cls, v: Any) -> str:
        if not v:
            return ""
        s = str(v).strip().capitalize()
        return s if s in ("Success", "Warning", "Danger", "Primary") else ""


class WorkflowTransition(BaseModel):
    """Transition edge between two workflow states."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    state: str = Field(..., description="Source state")
    action: str = Field(..., description="Action trigger button label")
    next_state: str = Field(..., description="Target state")
    allowed: str = Field(
        "System Manager", alias="allow_role", description="Role allowed to trigger transition"
    )
    condition: str | None = Field(None, description="Python evaluation condition expression string")
    allow_self_approval: Literal[0, 1] = Field(1, description="Allow self approval (1 or 0)")

    @field_validator("allowed", mode="before")
    @classmethod
    def coerce_allowed(cls, v: Any) -> str:
        if isinstance(v, dict):
            return str(v.get("role") or v.get("name") or "System Manager")
        return str(v).strip() if v else "System Manager"

    @field_validator("allow_self_approval", mode="before")
    @classmethod
    def coerce_self_approval(cls, v: Any) -> int:
        if isinstance(v, bool):
            return 1 if v else 0
        try:
            return 1 if int(v) else 0
        except (ValueError, TypeError):
            return 1


class WorkflowSpec(BaseModel):
    """Full Frappe Workflow definition."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: str = Field(..., description="Unique workflow name")
    document_type: str = Field(..., alias="doctype", description="Target DocType name")
    workflow_state_field: str = Field("workflow_state", description="State fieldname on target DocType")
    is_active: Literal[0, 1] = Field(1, description="Workflow active flag (1 or 0)")
    send_email_alert: bool = False
    states: list[WorkflowState] = Field(default_factory=list)
    transitions: list[WorkflowTransition] = Field(default_factory=list)

    @field_validator("is_active", mode="before")
    @classmethod
    def coerce_is_active(cls, v: Any) -> int:
        if isinstance(v, bool):
            return 1 if v else 0
        try:
            return 1 if int(v) else 0
        except (ValueError, TypeError):
            return 1


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

    @model_validator(mode="before")
    @classmethod
    def pre_validate_metadata(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)

        # 1. Resolve app_name & title
        raw_name = d.get("app_name") or d.get("name") or d.get("appName") or d.get("title") or "custom_app"
        s = re.sub(r"[^\w\s-]", "", str(raw_name)).strip().lower()
        snake = re.sub(r"[\s-]+", "_", s)
        if not snake or not snake[0].isalpha():
            snake = f"app_{snake}" if snake else "custom_app"

        if not d.get("app_name"):
            d["app_name"] = snake
        else:
            norm_name = str(d["app_name"]).strip().lower().replace("-", "_")
            norm_name = re.sub(r"[^\w]", "_", norm_name)
            if not norm_name or not norm_name[0].isalpha():
                norm_name = f"app_{norm_name}" if norm_name else "custom_app"
            d["app_name"] = norm_name

        if not d.get("title"):
            raw_title = d.get("title") or d.get("name") or d.get("app_title") or snake.replace("_", " ").title()
            d["title"] = str(raw_title).strip() or "Custom App"

        # 2. Normalize roles: must be list[str]
        raw_roles = d.get("roles")
        cleaned_roles: list[str] = []
        if isinstance(raw_roles, list):
            for r in raw_roles:
                if isinstance(r, dict):
                    role_str = (
                        r.get("role")
                        or r.get("name")
                        or r.get("label")
                        or r.get("title")
                        or ""
                    )
                    if role_str and str(role_str).strip():
                        cleaned_roles.append(str(role_str).strip())
                elif isinstance(r, str) and r.strip():
                    cleaned_roles.append(r.strip())
        elif isinstance(raw_roles, str) and raw_roles.strip():
            cleaned_roles = [part.strip() for part in re.split(r"[,;\n]", raw_roles) if part.strip()]

        if not cleaned_roles:
            cleaned_roles = ["System Manager"]
        elif "System Manager" not in cleaned_roles:
            cleaned_roles.append("System Manager")

        # Deduplicate while preserving order
        d["roles"] = list(dict.fromkeys(cleaned_roles))

        # 3. Normalize modules: must be list[str]
        raw_modules = d.get("modules")
        cleaned_modules: list[str] = []
        if isinstance(raw_modules, list):
            for m in raw_modules:
                if isinstance(m, dict):
                    mod_str = m.get("name") or m.get("module") or m.get("module_name") or ""
                    if mod_str and str(mod_str).strip():
                        cleaned_modules.append(str(mod_str).strip())
                elif isinstance(m, str) and m.strip():
                    cleaned_modules.append(m.strip())
        elif isinstance(raw_modules, str) and raw_modules.strip():
            cleaned_modules = [m.strip() for m in raw_modules.split(",") if m.strip()]

        d["modules"] = cleaned_modules or ["Custom"]

        return d

    @field_validator("app_name")
    @classmethod
    def app_name_snake_case(cls, v: str) -> str:
        s = v.strip().lower().replace("-", "_")
        s = re.sub(r"[^\w]", "_", s)
        if not s or not s[0].isalpha():
            return f"app_{s}" if s else "custom_app"
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

    @model_validator(mode="before")
    @classmethod
    def pre_validate_spec(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)

        # Force spec_version to "2.0"
        d["spec_version"] = "2.0"

        # Coerce status
        valid_statuses = {"ready", "needs_input", "drafting", "validating", "failed"}
        if d.get("status") not in valid_statuses:
            d["status"] = "ready" if (d.get("app") or d.get("doctypes")) else "needs_input"

        # If app is None or missing, but top-level has doctypes or app metadata
        if not d.get("app"):
            if "doctypes" in d or "app_name" in d or "name" in d:
                meta_keys = {
                    "app_name", "name", "title", "description", "publisher", "email",
                    "license", "version", "frappe_version", "requires_erpnext", "modules",
                    "roles", "doctypes", "workflows", "server_scripts", "client_scripts",
                    "reports", "number_cards", "dashboard_charts", "workspaces",
                }
                app_payload = {k: d[k] for k in meta_keys if k in d}
                d["app"] = app_payload

        return d

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
