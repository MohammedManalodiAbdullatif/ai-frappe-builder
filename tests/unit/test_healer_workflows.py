import pytest
from ai_frappe_builder.agents.healer import heal_workflow_errors, HealerAgent, HealerInput
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


@pytest.mark.asyncio
async def test_healer_fixes_wf_errors():
    spec = AppSpecV2(
        status="drafting",
        app=AppMetadata(
            app_name="car_rental",
            title="Car Rental",
            modules=["Fleet"],
            roles=["Rental Agent"],
            doctypes=[
                DocTypeSpec(
                    name="Rental Agreement",
                    module="Fleet",
                    is_submittable=False,  # WF007 error
                    fields=[
                        FieldSpec(fieldname="agreement_no", label="Agreement No", fieldtype="Data"),
                        # WF005 error: missing workflow_state
                    ],
                    permissions=[
                        PermissionSpec(role="Rental Agent", read=True, write=True),
                        # WF004 error: Fleet Manager missing
                    ],
                )
            ],
            workflows=[
                WorkflowSpec(
                    name="Rental Agreement Workflow",
                    document_type="Rental Agreement",
                    states=[
                        WorkflowState(state="Draft", doc_status=0, allow_edit="Rental Agent"),
                        # WF001 error: Active state missing from states[]
                    ],
                    transitions=[
                        WorkflowTransition(state="Draft", action="Activate", next_state="Active", allowed="Rental Agent"),
                        # WF009 error: duplicate transition
                        WorkflowTransition(state="Draft", action="Activate", next_state="Active", allowed="Rental Agent"),
                    ],
                )
            ],
        )
    )

    report = validate_spec(spec)
    assert not report.is_valid

    patch = heal_workflow_errors(spec, report)
    assert len(patch.operations) > 0

    # Apply patch
    updated_dict = patch.apply(spec.model_dump(exclude_none=True))
    healed_spec = AppSpecV2.model_validate(updated_dict)

    # Re-validate
    new_report = validate_spec(healed_spec)
    wf_errors = [e for e in new_report.errors if "[WF" in e]
    assert len(wf_errors) == 0, f"Expected 0 WF errors after heal, got: {wf_errors}"


@pytest.mark.asyncio
async def test_healer_does_not_invent_states_for_unreachable_wf003():
    spec = AppSpecV2(
        status="drafting",
        app=AppMetadata(
            app_name="car_rental",
            title="Car Rental",
            modules=["Fleet"],
            roles=["Rental Agent"],
            doctypes=[
                DocTypeSpec(
                    name="Rental Agreement",
                    module="Fleet",
                    is_submittable=True,
                    fields=[
                        FieldSpec(fieldname="workflow_state", label="Workflow State", fieldtype="Select", options="Draft\nActive\nOrphan", read_only=True),
                    ],
                    permissions=[
                        PermissionSpec(role="System Manager", read=True, write=True, create=True, delete=True),
                        PermissionSpec(role="Rental Agent", read=True, write=True, submit=True),
                    ],
                )
            ],
            workflows=[
                WorkflowSpec(
                    name="Rental Agreement Workflow",
                    document_type="Rental Agreement",
                    states=[
                        WorkflowState(state="Draft", doc_status=0, allow_edit="Rental Agent"),
                        WorkflowState(state="Active", doc_status=1, allow_edit="Rental Agent"),
                        WorkflowState(state="Orphan", doc_status=1, allow_edit="Rental Agent"),
                    ],
                    transitions=[
                        WorkflowTransition(state="Draft", action="Activate", next_state="Active", allowed="Rental Agent"),
                    ],
                )
            ],
        )
    )

    report = validate_spec(spec)
    assert any("[WF003]" in e for e in report.errors)

    healer = HealerAgent()
    patch = await healer.run(HealerInput(current_spec=spec, validation_report=report))
    # Should not produce patch operations inventing transitions/states for WF003
    assert len(patch.operations) == 0
