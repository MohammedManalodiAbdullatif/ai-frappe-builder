import json
from pathlib import Path
import pytest
from ai_frappe_builder.agents.orchestrator import Orchestrator, OrchestratorSession, OrchestratorState
from ai_frappe_builder.models.migration import migrate_v1_to_v2
from ai_frappe_builder.validator.rule_engine import validate_spec

GOLDEN_DIR = Path(__file__).resolve().parent.parent / "golden"


@pytest.mark.asyncio
async def test_differ_post_ready_incremental_edit():
    # Load car_rental golden spec
    with open(GOLDEN_DIR / "car_rental.json", encoding="utf-8") as f:
        spec_dict = json.load(f)

    spec = migrate_v1_to_v2(spec_dict)
    assert validate_spec(spec).is_valid

    # Setup orchestrator in DONE (Ready) state
    orchestrator = Orchestrator()
    session = OrchestratorSession(
        session_id="test-post-ready",
        state=OrchestratorState.DONE,
        spec=spec,
    )

    initial_dt_count = len(session.spec.app.doctypes)
    initial_wf_count = len(session.spec.app.workflows)
    target_dt = next(d for d in session.spec.app.doctypes if d.name == "Rental Agreement")
    initial_field_count = len(target_dt.fields)

    # User requests an incremental addition post-Ready
    user_msg = "add an insurance_expiry date field to Rental Agreement"
    result = await orchestrator.handle_user_message(session, user_msg)

    assert result["status"] == "ready"
    assert session.state == OrchestratorState.DONE

    # Verify isolated change: only insurance_expiry was added
    updated_dt = next(d for d in session.spec.app.doctypes if d.name == "Rental Agreement")
    assert len(updated_dt.fields) == initial_field_count + 1
    new_field = next((f for f in updated_dt.fields if f.fieldname == "insurance_expiry"), None)
    assert new_field is not None
    assert new_field.fieldtype == "Date"
    assert new_field.label == "Insurance Expiry"

    # Verify all other doctypes and workflows intact
    assert len(session.spec.app.doctypes) == initial_dt_count
    assert len(session.spec.app.workflows) == initial_wf_count

    # Spec remains valid
    report = validate_spec(session.spec)
    assert report.is_valid is True
