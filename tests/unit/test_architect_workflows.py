import pytest
from ai_frappe_builder.agents.architect import normalize_workflows
from ai_frappe_builder.models.app_spec_v2 import (
    AppMetadata,
    AppSpecV2,
    DocTypeSpec,
    FieldSpec,
    PermissionSpec,
    WorkflowSpec,
    WorkflowState,
    WorkflowTransition,
)
from ai_frappe_builder.validator.rule_engine import validate_spec


def test_normalize_workflows_synthesizes_for_status_field():
    spec = AppSpecV2(
        status="drafting",
        app=AppMetadata(
            app_name="car_rental",
            title="Car Rental",
            modules=["Fleet"],
            roles=["Rental Agent"],
            doctypes=[
                DocTypeSpec(
                    name="Rental Booking",
                    module="Fleet",
                    fields=[
                        FieldSpec(fieldname="customer", label="Customer", fieldtype="Data"),
                        FieldSpec(fieldname="status", label="Status", fieldtype="Select", options="Draft\nConfirmed\nCompleted\nCancelled"),
                    ],
                    permissions=[
                        PermissionSpec(role="Rental Agent", read=True, write=True),
                    ],
                )
            ],
            workflows=[],
        )
    )

    normalized = normalize_workflows(spec)
    assert len(normalized.app.workflows) == 1
    wf = normalized.app.workflows[0]
    assert wf.document_type == "Rental Booking"
    assert len(wf.states) == 4

    dt = normalized.app.doctypes[0]
    # Check that manual status field was removed
    fieldnames = [f.fieldname for f in dt.fields]
    assert "status" not in fieldnames
    assert "workflow_state" in fieldnames

    wf_field = next(f for f in dt.fields if f.fieldname == "workflow_state")
    assert wf_field.fieldtype == "Select"
    assert wf_field.read_only is True
    assert wf_field.options == "Draft\nConfirmed\nCompleted\nCancelled"


def test_normalize_workflows_fixes_existing_workflow():
    spec = AppSpecV2(
        status="drafting",
        app=AppMetadata(
            app_name="fleet_mgmt",
            title="Fleet Management",
            modules=["Fleet"],
            roles=["Rental Agent"],
            doctypes=[
                DocTypeSpec(
                    name="Rental Agreement",
                    module="Fleet",
                    is_submittable=False,
                    fields=[
                        FieldSpec(fieldname="agreement_no", label="Agreement No", fieldtype="Data"),
                        FieldSpec(fieldname="status", label="Status", fieldtype="Select", options="Draft\nActive\nClosed"),
                    ],
                    permissions=[
                        PermissionSpec(role="System Manager", read=True, write=True),
                        PermissionSpec(role="Rental Agent", read=True, write=True),
                    ],
                )
            ],
            workflows=[
                WorkflowSpec(
                    name="Rental Agreement Workflow",
                    document_type="Rental Agreement",
                    states=[
                        WorkflowState(state="Draft", doc_status=0, allow_edit="Rental Agent"),
                        WorkflowState(state="Active", doc_status=1, allow_edit="Fleet Manager"),
                        WorkflowState(state="Closed", doc_status=1, allow_edit="Fleet Manager"),
                    ],
                    transitions=[
                        WorkflowTransition(state="Draft", action="Activate", next_state="Active", allowed="Rental Agent"),
                        WorkflowTransition(state="Active", action="Close", next_state="Closed", allowed="Fleet Manager"),
                    ],
                )
            ],
        )
    )

    normalized = normalize_workflows(spec)
    dt = normalized.app.doctypes[0]

    # 1. is_submittable should be True
    assert dt.is_submittable is True

    # 2. Duplicate status field removed
    fieldnames = [f.fieldname for f in dt.fields]
    assert "status" not in fieldnames
    assert "workflow_state" in fieldnames

    # 3. Fleet Manager added to app.roles
    assert "Fleet Manager" in normalized.app.roles

    # 4. Fleet Manager permission row added to dt
    perm_roles = {p.role: p for p in dt.permissions}
    assert "Fleet Manager" in perm_roles
    assert perm_roles["Fleet Manager"].read is True
    assert perm_roles["Fleet Manager"].write is True
    assert perm_roles["Fleet Manager"].submit is True

    # 5. Must pass rule engine
    report = validate_spec(normalized)
    wf_errors = [e for e in report.errors if "[WF" in e]
    assert len(wf_errors) == 0, f"Expected 0 WF errors, got: {wf_errors}"
