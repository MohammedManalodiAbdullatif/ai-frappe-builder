"""
ai_frappe_builder.models — Unified data models for Frappe App Specs (v1 and v2), RFC 6902 patches, and validation.
"""

from ai_frappe_builder.models.api_models import (
    ApplyResponse,
    ChatMessageRequest,
    ChatResponse,
    ChatStartRequest,
    PlanResponse,
)
from ai_frappe_builder.models.app_spec_v2 import (
    AppMetadata,
    AppSpecV2,
    ClientScriptSpec,
    DashboardChartSpec,
    DocTypeKind,
    DocTypeSpec,
    FieldSpec,
    FrappeFieldType,
    InterviewQuestion,
    NumberCardSpec,
    PermissionSpec,
    QuestionOption,
    ReportSpec,
    ServerScriptSpec,
    WorkflowSpec,
    WorkflowState,
    WorkflowTransition,
    WorkspaceLink,
    WorkspaceShortcut,
    WorkspaceSpec,
)
from ai_frappe_builder.models.migration import (
    migrate_v1_to_v2,
)
from ai_frappe_builder.models.patch import (
    PatchOperation,
    SpecPatch,
    make_spec_patch,
)
from ai_frappe_builder.models.v1_compat import AppSpec
from ai_frappe_builder.models.validation import (
    FixHint,
    ValidationErrorItem,
    ValidationReport,
)

__all__ = [
    # v2 models
    "AppMetadata",
    "AppSpecV2",
    "ClientScriptSpec",
    "DashboardChartSpec",
    "DocTypeKind",
    "DocTypeSpec",
    "FieldSpec",
    "FrappeFieldType",
    "InterviewQuestion",
    "NumberCardSpec",
    "PermissionSpec",
    "QuestionOption",
    "ReportSpec",
    "ServerScriptSpec",
    "WorkflowSpec",
    "WorkflowState",
    "WorkflowTransition",
    "WorkspaceLink",
    "WorkspaceShortcut",
    "WorkspaceSpec",
    # Patch models
    "PatchOperation",
    "SpecPatch",
    "make_spec_patch",
    # Validation models
    "FixHint",
    "ValidationErrorItem",
    "ValidationReport",
    # Migration
    "migrate_v1_to_v2",
    # API models
    "ApplyResponse",
    "ChatMessageRequest",
    "ChatResponse",
    "ChatStartRequest",
    "PlanResponse",
    # Legacy v1
    "AppSpec",
]
