"""
ai_frappe_builder.validator — Deterministic validation engine for Frappe applications.
"""

from __future__ import annotations

from typing import Any

from ai_frappe_builder.models.validation import FixHint, ValidationErrorItem, ValidationReport
from ai_frappe_builder.validator.catalog import (
    get_conventions_catalog,
    get_erpnext_doctypes_catalog,
    get_fieldtypes_catalog,
    get_reserved_fieldnames,
    get_standard_doctype_names,
)
from ai_frappe_builder.validator.rule_engine import RuleEngine, validate_spec

RESERVED_FIELDNAMES = get_reserved_fieldnames()
STANDARD_CORE_DOCTYPES = get_standard_doctype_names()


def validate(spec: Any, site_context: dict[str, Any] | None = None) -> tuple[bool, list[str]]:
    """
    Backward-compatible validator wrapper returning (is_valid, messages).
    """
    report = validate_spec(spec, site_context)
    messages = list(report.errors) + list(report.warnings)
    return report.is_valid, messages


async def validate_with_jev(
    spec: Any,
    site_context: dict[str, Any] | None = None,
) -> tuple[bool, list[str], str]:
    """
    Combined validation:
      1. Deterministic Python hard rules
      2. Jev decision gate (readiness score)
    """
    is_valid, messages = validate(spec, site_context)
    readiness_score = "Ship-ready" if is_valid else "Major gaps"

    try:
        from ai_frappe_builder import decide

        app_dict = None
        if hasattr(spec, "app"):
            app_dict = (
                spec.app
                if isinstance(spec.app, dict)
                else (spec.app.model_dump() if spec.app else None)
            )
        elif isinstance(spec, dict):
            app_dict = spec.get("app")

        if app_dict:
            jev_eval = await decide.judge_spec_gate(app_dict, site_context or {})
            readiness_score = jev_eval.get("readiness_score", readiness_score)
            if jev_eval.get("has_duplicates"):
                messages.append(
                    "WARNING: [Jev] A planned DocType may duplicate existing core site functionality."
                )
    except Exception:
        pass

    return is_valid, messages, readiness_score


__all__ = [
    "FixHint",
    "RESERVED_FIELDNAMES",
    "RuleEngine",
    "STANDARD_CORE_DOCTYPES",
    "ValidationErrorItem",
    "ValidationReport",
    "get_conventions_catalog",
    "get_erpnext_doctypes_catalog",
    "get_fieldtypes_catalog",
    "validate",
    "validate_spec",
    "validate_with_jev",
]
