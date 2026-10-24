"""
rule_engine.py — Deterministic rule engine orchestrator.
"""

from __future__ import annotations

from typing import Any

from ai_frappe_builder.models.app_spec_v2 import AppSpecV2
from ai_frappe_builder.models.migration import migrate_v1_to_v2
from ai_frappe_builder.models.validation import ValidationReport
from ai_frappe_builder.validator.catalog import get_standard_doctype_names
from ai_frappe_builder.validator.rules import (
    MAX_FIELDS_WARNING,
    validate_autoname_scheme,
    validate_child_table_rules,
    validate_circular_mandatory_links,
    validate_doctype_naming,
    validate_fieldnames,
    validate_fieldtypes_and_options,
    validate_layout_breaks,
    validate_permissions_system_manager,
    validate_workflows,
)


class RuleEngine:
    """Deterministic validation rule engine for Frappe specs."""

    def __init__(self, site_context: dict[str, Any] | None = None) -> None:
        self.site_context = site_context or {}

    def run(self, spec: AppSpecV2) -> ValidationReport:
        report = ValidationReport()

        if spec.status not in ("ready", "drafting", "validating"):
            report.add_error(
                rule="spec_status_not_ready",
                message=f"Spec status is '{spec.status}' — cannot validate incomplete spec.",
            )
            return report

        if not spec.app:
            report.add_error(
                rule="spec_missing_app",
                message="Spec does not contain an app definition.",
            )
            return report

        doctypes = spec.app.doctypes
        if not doctypes:
            report.add_warning(
                rule="app_has_no_doctypes",
                message="App specification contains zero DocTypes.",
            )
            return report

        # Compile known DocTypes
        site_doctype_names = {
            dt["name"] if isinstance(dt, dict) else str(dt)
            for dt in self.site_context.get("doctypes", [])
        }
        standard_names = get_standard_doctype_names()
        spec_doctype_names = {dt.name for dt in doctypes}
        all_known = site_doctype_names | standard_names | spec_doctype_names
        child_doctype_names = {dt.name for dt in doctypes if dt.istable}

        # Track referenced child tables across all doctypes
        referenced_child_doctypes: set[str] = set()
        for dt in doctypes:
            for f in dt.fields:
                if f.fieldtype in ("Table", "Table MultiSelect") and f.options:
                    referenced_child_doctypes.add(f.options)

        doctypes_map = {dt.name: dt for dt in doctypes}

        # Validate each DocType
        for dt in doctypes:
            validate_doctype_naming(dt, report)
            validate_fieldnames(dt, report)
            validate_fieldtypes_and_options(dt, all_known, child_doctype_names, report)
            validate_child_table_rules(dt, referenced_child_doctypes, report)
            validate_permissions_system_manager(dt, report)
            validate_autoname_scheme(dt, report)
            validate_layout_breaks(dt, report)

            # Check max fields warning
            real_fields = [
                f
                for f in dt.fields
                if f.fieldtype
                not in ("Section Break", "Column Break", "Tab Break", "Heading", "Fold")
            ]
            if len(real_fields) > MAX_FIELDS_WARNING:
                report.add_warning(
                    rule="max_fields_exceeded",
                    message=f"DocType '{dt.name}' has {len(real_fields)} data fields (recommended max {MAX_FIELDS_WARNING}).",
                    doctype=dt.name,
                )

        # Cross-DocType & Workflow validation
        validate_workflows(spec.app.workflows, doctypes_map, report)
        validate_circular_mandatory_links(doctypes, report)

        return report


def validate_spec(
    spec: Any,
    site_context: dict[str, Any] | None = None,
) -> ValidationReport:
    """
    Main entry point: validates an AppSpecV2, legacy AppSpec, or dictionary.
    """
    if isinstance(spec, AppSpecV2):
        spec_v2 = spec
    elif isinstance(spec, dict):
        spec_v2 = migrate_v1_to_v2(spec)
    elif hasattr(spec, "model_dump"):
        spec_v2 = migrate_v1_to_v2(spec.model_dump())
    else:
        report = ValidationReport()
        report.add_error("invalid_spec_type", f"Cannot validate object of type {type(spec)}")
        return report

    engine = RuleEngine(site_context=site_context)
    return engine.run(spec_v2)
