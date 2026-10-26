"""
test_validator.py — Exhaustive deterministic validator and property-based test suite.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from ai_frappe_builder.models import (
    AppMetadata,
    AppSpecV2,
    DocTypeSpec,
    FieldSpec,
    PermissionSpec,
    WorkflowSpec,
    WorkflowState,
    WorkflowTransition,
)
from ai_frappe_builder.validator import validate, validate_spec


def _build_valid_car_rental_spec() -> AppSpecV2:
    child_table = DocTypeSpec(
        name="Rental Addon Item",
        module="Fleet",
        istable=True,
        autoname="hash",
        fields=[
            FieldSpec(fieldname="addon_name", label="Addon Name", fieldtype="Data", reqd=True),
            FieldSpec(fieldname="price", label="Price", fieldtype="Currency"),
        ],
        permissions=[],
    )

    parent_doc = DocTypeSpec(
        name="Rental Agreement",
        module="Fleet",
        istable=False,
        is_submittable=True,
        autoname="Prompt",
        fields=[
            FieldSpec(
                fieldname="customer",
                label="Customer",
                fieldtype="Link",
                options="Customer",
                reqd=True,
            ),
            FieldSpec(
                fieldname="company", label="Company", fieldtype="Link", options="Company", reqd=True
            ),
            FieldSpec(
                fieldname="items", label="Addons", fieldtype="Table", options="Rental Addon Item"
            ),
            FieldSpec(fieldname="start_date", label="Start Date", fieldtype="Date", reqd=True),
            FieldSpec(
                fieldname="workflow_state",
                label="Workflow State",
                fieldtype="Select",
                options="Draft\nActive",
                read_only=True,
                in_list_view=True,
                in_standard_filter=True,
                allow_on_submit=True,
            ),
        ],
        permissions=[
            PermissionSpec(role="System Manager", read=True, write=True, create=True, delete=True),
        ],
    )

    workflow = WorkflowSpec(
        name="Rental Workflow",
        document_type="Rental Agreement",
        states=[
            WorkflowState(state="Draft", doc_status=0, allow_edit="System Manager"),
            WorkflowState(state="Active", doc_status=1, allow_edit="System Manager"),
        ],
        transitions=[
            WorkflowTransition(
                state="Draft", action="Activate", next_state="Active", allowed="System Manager"
            ),
        ],
    )

    app_meta = AppMetadata(
        app_name="car_rental",
        title="Car Rental",
        doctypes=[child_table, parent_doc],
        workflows=[workflow],
    )

    return AppSpecV2(status="ready", spec_version="2.0", app=app_meta)


def test_valid_spec_passes_with_zero_errors() -> None:
    spec = _build_valid_car_rental_spec()
    report = validate_spec(spec)
    assert report.is_valid is True, f"Expected valid spec, got errors: {report.errors}"
    assert len(report.errors) == 0


def test_rule_1_title_case_enforcement() -> None:
    spec = _build_valid_car_rental_spec()
    assert spec.app is not None
    # Bypass pydantic validation for testing rule engine rejection
    dt = spec.app.doctypes[1]
    object.__setattr__(dt, "name", "rental agreement")

    report = validate_spec(spec)
    assert report.is_valid is False
    assert any("doctype_name_title_case" in e for e in report.errors)


def test_rule_2_reserved_fieldnames() -> None:
    spec = _build_valid_car_rental_spec()
    assert spec.app is not None
    spec.app.doctypes[1].fields.append(
        FieldSpec(fieldname="docstatus", label="Doc Status", fieldtype="Int")
    )
    report = validate_spec(spec)
    assert report.is_valid is False
    assert any("reserved_fieldname" in e for e in report.errors)
    assert any(h.rule == "reserved_fieldname" for h in report.fix_hints)


def test_rule_3_link_to_unknown_doctype() -> None:
    spec = _build_valid_car_rental_spec()
    assert spec.app is not None
    spec.app.doctypes[1].fields.append(
        FieldSpec(
            fieldname="fake_link", label="Fake", fieldtype="Link", options="NonExistentDocType"
        )
    )
    report = validate_spec(spec)
    assert report.is_valid is False
    assert any("link_unknown_target" in e for e in report.errors)


def test_rule_4_table_pointing_to_non_child() -> None:
    spec = _build_valid_car_rental_spec()
    assert spec.app is not None
    # Table pointing to non-child
    spec.app.doctypes[1].fields.append(
        FieldSpec(
            fieldname="bad_table", label="Bad Table", fieldtype="Table", options="Rental Agreement"
        )
    )
    report = validate_spec(spec)
    assert report.is_valid is False
    assert any("table_target_not_child" in e for e in report.errors)


def test_rule_5_child_table_permissions_forbidden() -> None:
    spec = _build_valid_car_rental_spec()
    assert spec.app is not None
    spec.app.doctypes[0].permissions = [
        PermissionSpec(role="System Manager", read=True, write=True)
    ]
    report = validate_spec(spec)
    assert report.is_valid is False
    assert any("child_table_permissions" in e for e in report.errors)


def test_submittable_consistency_mismatch() -> None:
    spec = _build_valid_car_rental_spec()
    assert spec.app is not None
    # Set parent is_submittable to False while workflow transitions to doc_status 1
    spec.app.doctypes[1].is_submittable = False
    report = validate_spec(spec)
    assert report.is_valid is False
    assert any("workflow_submittable_mismatch" in e or "WF007" in e for e in report.errors)


def test_circular_mandatory_links_detected() -> None:
    dt1 = DocTypeSpec(
        name="Doc One",
        module="Test",
        fields=[
            FieldSpec(
                fieldname="ref_two", label="Ref Two", fieldtype="Link", options="Doc Two", reqd=True
            )
        ],
        permissions=[
            PermissionSpec(role="System Manager", read=True, write=True, create=True, delete=True)
        ],
    )
    dt2 = DocTypeSpec(
        name="Doc Two",
        module="Test",
        fields=[
            FieldSpec(
                fieldname="ref_one", label="Ref One", fieldtype="Link", options="Doc One", reqd=True
            )
        ],
        permissions=[
            PermissionSpec(role="System Manager", read=True, write=True, create=True, delete=True)
        ],
    )
    spec = AppSpecV2(
        status="ready",
        spec_version="2.0",
        app=AppMetadata(app_name="circular_app", title="Circular App", doctypes=[dt1, dt2]),
    )
    report = validate_spec(spec)
    assert report.is_valid is False
    assert any("circular_mandatory_link" in e for e in report.errors)


def test_backward_compatible_validate_function() -> None:
    spec = _build_valid_car_rental_spec()
    is_valid, messages = validate(spec)
    assert is_valid is True
    assert isinstance(messages, list)


@given(st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_"))
def test_hypothesis_fuzz_fieldnames(fname: str) -> None:
    """Hypothesis test ensuring arbitrary fieldnames never crash the validator."""
    try:
        f = FieldSpec(fieldname=fname, label="Label", fieldtype="Data")
        dt = DocTypeSpec(
            name="Fuzz Doc",
            fields=[f],
            permissions=[
                PermissionSpec(
                    role="System Manager", read=True, write=True, create=True, delete=True
                )
            ],
        )
        spec = AppSpecV2(
            status="ready",
            spec_version="2.0",
            app=AppMetadata(app_name="fuzz_app", title="Fuzz App", doctypes=[dt]),
        )
        report = validate_spec(spec)
        assert isinstance(report.is_valid, bool)
    except ValueError:
        # Pydantic fieldname validator rejected invalid snake_case (e.g. leading digit)
        pass
