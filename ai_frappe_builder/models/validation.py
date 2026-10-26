"""
validation.py — Structured validation report models for Frappe App specs.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FixHint(BaseModel):
    """Actionable hint suggesting how to fix a validation error or warning."""

    rule: str
    rule_id: str | None = None
    path: str | None = None
    doctype: str | None = None
    field: str | None = None
    message: str
    suggested_patch: dict[str, Any] | None = None


class ValidationErrorItem(BaseModel):
    """Detailed validation issue."""

    rule: str
    rule_id: str | None = None
    path: str | None = None
    doctype: str | None = None
    field: str | None = None
    message: str
    severity: str = "error"  # error | warning


class ValidationReport(BaseModel):
    """
    Deterministic rule engine report for an AppSpec.
    Contains errors (blocking), warnings (non-blocking), and machine-actionable fix hints.
    """

    is_valid: bool = True
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    fix_hints: list[FixHint] = Field(default_factory=list)
    detailed_errors: list[ValidationErrorItem] = Field(default_factory=list)

    def add_error(
        self,
        rule: str,
        message: str,
        doctype: str | None = None,
        field: str | None = None,
        fix_hint: FixHint | None = None,
        path: str | None = None,
        rule_id: str | None = None,
    ) -> None:
        self.is_valid = False
        tag = rule_id or rule
        formatted = f"[{tag}] DocType '{doctype}': {message}" if doctype else f"[{tag}] {message}"
        self.errors.append(formatted)
        self.detailed_errors.append(
            ValidationErrorItem(
                rule=rule,
                rule_id=rule_id or rule,
                path=path,
                doctype=doctype,
                field=field,
                message=message,
                severity="error",
            )
        )
        if fix_hint:
            if not fix_hint.rule_id:
                fix_hint.rule_id = rule_id or rule
            if not fix_hint.path:
                fix_hint.path = path
            self.fix_hints.append(fix_hint)

    def add_warning(
        self,
        rule: str,
        message: str,
        doctype: str | None = None,
        field: str | None = None,
        fix_hint: FixHint | None = None,
        path: str | None = None,
        rule_id: str | None = None,
    ) -> None:
        tag = rule_id or rule
        formatted = f"[{tag}] DocType '{doctype}': {message}" if doctype else f"[{tag}] {message}"
        self.warnings.append(formatted)
        self.detailed_errors.append(
            ValidationErrorItem(
                rule=rule,
                rule_id=rule_id or rule,
                path=path,
                doctype=doctype,
                field=field,
                message=message,
                severity="warning",
            )
        )
        if fix_hint:
            if not fix_hint.rule_id:
                fix_hint.rule_id = rule_id or rule
            if not fix_hint.path:
                fix_hint.path = path
            self.fix_hints.append(fix_hint)
