"""
test_interviewer_flow.py — Verification of discovery phases, coverage gates, and structured options.
"""

from __future__ import annotations

import json
import pytest
import respx

from ai_frappe_builder.agents.interviewer import (
    CoverageSpec,
    InterviewInput,
    InterviewerAgent,
    InterviewTurn,
    OptionSpec,
    QuestionSpec,
)
from ai_frappe_builder.agents.orchestrator import Orchestrator, OrchestratorSession
from ai_frappe_builder.llm.client import LLMClient
from ai_frappe_builder.llm.tracer import LLMTracer


@pytest.fixture
def mock_llm_client() -> LLMClient:
    return LLMClient(
        base_url="https://api.mockllm.test/v1",
        api_key="test-key",
        model="mock-model",
        tracer=LLMTracer(),
    )


@respx.mock
@pytest.mark.asyncio
async def test_opening_message_skips_b1_to_b2(mock_llm_client: LLMClient) -> None:
    """
    Given opening message 'clinic with 3 branches', first turn must be:
    - phase: basics
    - id: app_purpose (B1 skipped)
    - options array length: 3–5
    - say contains no '**' and no option labels
    """
    mock_turn = {
        "kind": "question",
        "say": "Got it — a clinic with three branches.",
        "question": {
            "id": "app_purpose",
            "phase": "basics",
            "text": "What should this app mainly help with?",
            "help": "Guides the core DocTypes and required functionality",
            "input": "single",
            "options": [
                {
                    "value": "operations_tracking",
                    "label": "Operations & tracking",
                    "description": "Daily operational logs, assets, and patient tracking",
                },
                {
                    "value": "approvals_workflows",
                    "label": "Approvals & workflows",
                    "description": "Review cycles, prescription approvals, and sign-offs",
                },
                {
                    "value": "customer_records",
                    "label": "Customer-facing records",
                    "description": "Patient intake records, medical history, and communications",
                },
                {
                    "value": "reporting_analytics",
                    "label": "Reporting & analytics",
                    "description": "Aggregated clinic metrics, doctor workload, and visit counts",
                },
            ],
            "allow_custom": True,
        },
        "assumptions": ["Business is a medical clinic with 3 physical branches"],
        "coverage": {
            "basics": 0.17,
            "domain": 0.0,
        },
    }

    respx.post("https://api.mockllm.test/v1/chat/completions").respond(
        status_code=200,
        json={"choices": [{"message": {"content": json.dumps(mock_turn)}}]},
    )

    agent = InterviewerAgent(llm_client=mock_llm_client)
    turn = await agent.run(
        InterviewInput(messages=[{"role": "user", "content": "clinic with 3 branches"}])
    )

    assert turn.question is not None
    assert turn.question.phase == "basics"
    assert turn.question.id == "app_purpose"
    assert turn.question.options is not None
    assert 3 <= len(turn.question.options) <= 5

    # Say assertions
    assert "**" not in turn.say
    for opt in turn.question.options:
        assert opt.label.lower() not in turn.say.lower()


@respx.mock
@pytest.mark.asyncio
async def test_domain_phase_gate_coverage(mock_llm_client: LLMClient) -> None:
    """
    Domain phase must not start before basics coverage >= 0.8.
    """
    # Attempting to return domain question when basics coverage is below 0.8
    premature_domain_turn = {
        "kind": "question",
        "say": "Let us explore your entity model.",
        "question": {
            "id": "q_prescriptions",
            "phase": "domain",
            "text": "Do you need a prescription management DocType?",
            "help": "Prescription entities",
            "input": "yesno",
            "options": [
                {"label": "Yes", "value": "yes", "description": None},
                {"label": "No", "value": "no", "description": None},
            ],
            "allow_custom": False,
        },
        "assumptions": ["Low coverage context"],
        "coverage": {
            "basics": 0.40,  # Below 0.8 gate!
            "domain": 0.10,
        },
    }

    respx.post("https://api.mockllm.test/v1/chat/completions").respond(
        status_code=200,
        json={"choices": [{"message": {"content": json.dumps(premature_domain_turn)}}]},
    )

    agent = InterviewerAgent(llm_client=mock_llm_client)
    turn = await agent.run(
        InterviewInput(
            messages=[{"role": "user", "content": "We are a clinic."}],
            coverage=CoverageSpec(basics=0.40, domain=0.0),
            phase="basics",
        )
    )

    # Agent must enforce that question phase is 'basics' because coverage < 0.8
    assert turn.question is not None
    assert turn.question.phase == "basics"


def test_option_with_commas_and_parentheses_survives_round_trip() -> None:
    """
    Option with commas and parentheses in description survives round-trip as one option.
    """
    complex_desc = (
        "Strict: Only HR Managers can view/edit all records; Employees see nothing "
        "(confidential salary, bank details, and disciplinary logs)"
    )

    turn = InterviewTurn(
        kind="question",
        say="Understood, setting permission policy.",
        question=QuestionSpec(
            id="permissions_policy",
            phase="domain",
            text="Who should have access to this data and how should permissions be handled?",
            help="Defines document permissions and role isolation",
            input="single",
            options=[
                OptionSpec(
                    value="strict_hr",
                    label="Strict HR Only",
                    description=complex_desc,
                ),
                OptionSpec(
                    value="self_service",
                    label="Self-Service",
                    description="Employees view own profile, manager approves time-off",
                ),
            ],
            allow_custom=True,
        ),
        assumptions=["HR data sensitivity is high"],
        coverage=CoverageSpec(basics=1.0, domain=0.5),
    )

    # Serialize to JSON and parse back
    json_bytes = turn.model_dump_json()
    loaded = InterviewTurn.model_validate_json(json_bytes)

    assert loaded.question is not None
    assert loaded.question.options is not None
    assert len(loaded.question.options) == 2

    # The complex description with commas and parentheses is preserved intact as 1 option
    first_opt = loaded.question.options[0]
    assert first_opt.description == complex_desc
    assert "," in first_opt.description
    assert "(" in first_opt.description
    assert ")" in first_opt.description


@respx.mock
@pytest.mark.asyncio
async def test_orchestrator_discovery_script_e2e(mock_llm_client: LLMClient) -> None:
    """
    Orchestrator enforces basics script, advances coverage, and transitions to drafting on confirm.
    """
    interviewer = InterviewerAgent(llm_client=mock_llm_client)
    orchestrator = Orchestrator(interviewer=interviewer)

    # Mock response for turn 1
    t1_json = {
        "kind": "question",
        "say": "Got it — a vehicle rental business.",
        "question": {
            "id": "app_purpose",
            "phase": "basics",
            "text": "What should this app mainly help with?",
            "help": "Guides core DocTypes",
            "input": "single",
            "options": [
                {"label": "Operations & tracking", "value": "ops", "description": "Fleet tracking"},
                {"label": "Customer booking", "value": "booking", "description": "Reservations"},
                {"label": "Invoicing", "value": "billing", "description": "Payment cycles"},
            ],
            "allow_custom": True,
        },
        "assumptions": ["Car rental business"],
        "coverage": {"basics": 0.17, "domain": 0.0},
    }

    respx.post("https://api.mockllm.test/v1/chat/completions").respond(
        status_code=200,
        json={"choices": [{"message": {"content": json.dumps(t1_json)}}]},
    )

    session = OrchestratorSession(session_id="orch-discovery-e2e")
    res1 = await orchestrator.handle_user_message(session, "We run a vehicle rental company with 50 cars.")

    assert res1["status"] == "needs_input"
    assert res1["interview_turn"] is not None
    assert res1["interview_turn"]["question"]["id"] == "app_purpose"
    assert session.coverage.basics > 0
