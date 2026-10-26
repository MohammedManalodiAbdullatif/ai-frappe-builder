"""
test_agents.py — Contract tests verifying specialist agent I/O contracts and mocked LLM client flows.
"""

from __future__ import annotations

import json

import pytest
import respx

from ai_frappe_builder.agents import (
    ArchitectAgent,
    ArchitectInput,
    DifferAgent,
    DifferInput,
    InterviewerAgent,
    InterviewInput,
    InterviewTurn,
    Orchestrator,
    OrchestratorSession,
    OrchestratorState,
)
from ai_frappe_builder.events import event_manager
from ai_frappe_builder.llm.client import LLMClient
from ai_frappe_builder.llm.tracer import LLMTracer
from ai_frappe_builder.models import (
    AppMetadata,
    AppSpecV2,
    DocTypeSpec,
    PermissionSpec,
    SpecPatch,
)


@pytest.fixture
def mock_llm_client() -> LLMClient:
    return LLMClient(
        base_url="https://api.mockllm.test/v1",
        api_key="test-key",
        model="mock-model",
        tracer=LLMTracer(db_path=":memory:"),
    )


@respx.mock
@pytest.mark.asyncio
async def test_llm_client_completion_success(mock_llm_client: LLMClient) -> None:
    respx.post("https://api.mockllm.test/v1/chat/completions").respond(
        status_code=200,
        json={
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "kind": "done",
                                "say": "All requirements captured.",
                                "question": None,
                                "assumptions": ["car_rental", "Daily pricing"],
                                "coverage": {"basics": 1.0, "domain": 1.0},
                            }
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 50, "completion_tokens": 20},
        },
    )

    result = await mock_llm_client.complete(
        messages=[{"role": "user", "content": "I run a car rental business"}],
        response_schema=InterviewTurn,
    )
    assert isinstance(result, dict)
    assert result["kind"] == "done"
    assert "car_rental" in result["assumptions"]


@respx.mock
@pytest.mark.asyncio
async def test_interviewer_agent_contract(mock_llm_client: LLMClient) -> None:
    agent = InterviewerAgent(llm_client=mock_llm_client)

    turn_data = {
        "kind": "question",
        "say": "Got it — a car rental service.",
        "question": {
            "id": "q_fleet_type",
            "phase": "domain",
            "text": "What kind of vehicles do you offer?",
            "help": "Determines category fields",
            "input": "single",
            "options": [
                {"label": "Sedans & SUVs", "value": "passenger", "description": "Standard passenger cars"},
                {"label": "Commercial Vans", "value": "commercial", "description": "Cargo and passenger vans"},
            ],
            "allow_custom": True,
        },
        "assumptions": ["USD currency"],
        "coverage": {
            "basics": 0.85,
            "domain": 0.20,
        },
    }

    respx.post("https://api.mockllm.test/v1/chat/completions").respond(
        status_code=200,
        json={"choices": [{"message": {"content": json.dumps(turn_data)}}]},
    )

    turn = await agent.run(InterviewInput(messages=[{"role": "user", "content": "Start"}]))
    assert isinstance(turn, InterviewTurn)
    assert turn.ready is False
    assert turn.question is not None
    assert turn.question.id == "q_fleet_type"
    assert len(turn.question.options) == 2


@respx.mock
@pytest.mark.asyncio
async def test_architect_agent_contract(mock_llm_client: LLMClient) -> None:
    agent = ArchitectAgent(llm_client=mock_llm_client)

    app_spec_data = {
        "spec_version": "2.0",
        "status": "ready",
        "app": {
            "app_name": "car_rental",
            "title": "Car Rental",
            "doctypes": [
                {
                    "name": "Vehicle",
                    "fields": [{"fieldname": "plate", "label": "Plate", "fieldtype": "Data"}],
                    "permissions": [
                        {
                            "role": "System Manager",
                            "read": True,
                            "write": True,
                            "create": True,
                            "delete": True,
                        }
                    ],
                }
            ],
            "workflows": [],
        },
    }

    respx.post("https://api.mockllm.test/v1/chat/completions").respond(
        status_code=200,
        json={"choices": [{"message": {"content": json.dumps(app_spec_data)}}]},
    )

    spec = await agent.run(
        ArchitectInput(transcript=[{"role": "user", "content": "Design car rental"}])
    )
    assert isinstance(spec, AppSpecV2)
    assert spec.status == "ready"
    assert spec.app is not None
    assert spec.app.app_name == "car_rental"


@respx.mock
@pytest.mark.asyncio
async def test_differ_agent_contract(mock_llm_client: LLMClient) -> None:
    agent = DifferAgent(llm_client=mock_llm_client)

    patch_data = {
        "description": "Add vin field to Vehicle",
        "operations": [
            {
                "op": "add",
                "path": "/app/doctypes/0/fields/-",
                "value": {"fieldname": "vin", "label": "VIN", "fieldtype": "Data"},
            }
        ],
    }

    respx.post("https://api.mockllm.test/v1/chat/completions").respond(
        status_code=200,
        json={"choices": [{"message": {"content": json.dumps(patch_data)}}]},
    )

    current_spec = AppSpecV2(
        status="ready",
        spec_version="2.0",
        app=AppMetadata(
            app_name="car_rental",
            title="Car Rental",
            doctypes=[
                DocTypeSpec(
                    name="Vehicle",
                    fields=[],
                    permissions=[
                        PermissionSpec(
                            role="System Manager", read=True, write=True, create=True, delete=True
                        )
                    ],
                )
            ],
        ),
    )

    patch = await agent.run(DifferInput(current_spec=current_spec, user_request="Add VIN field"))
    assert isinstance(patch, SpecPatch)
    assert len(patch.operations) == 1
    assert patch.operations[0].op == "add"


@pytest.mark.asyncio
async def test_sse_event_manager_publish_subscribe() -> None:
    session_id = "test-session-123"
    received_events = []

    async def reader() -> None:
        async for event in event_manager.subscribe(session_id):
            received_events.append(event)
            if len(received_events) >= 2:
                break

    import asyncio

    reader_task = asyncio.create_task(reader())
    await asyncio.sleep(0.01)

    await event_manager.publish(session_id, "state_change", {"to_state": "discovery"})
    await event_manager.publish(session_id, "token", {"token": "Hello"})

    await asyncio.wait_for(reader_task, timeout=2.0)
    assert len(received_events) == 2
    assert received_events[0].event_type == "state_change"
    assert received_events[1].event_type == "token"


@respx.mock
@pytest.mark.asyncio
async def test_orchestrator_discovery_flow(mock_llm_client: LLMClient) -> None:
    interviewer = InterviewerAgent(llm_client=mock_llm_client)
    orchestrator = Orchestrator(interviewer=interviewer)

    turn_data = {
        "kind": "question",
        "say": "Got it — a car rental service.",
        "question": {
            "id": "app_purpose",
            "phase": "basics",
            "text": "What should this app mainly help with?",
            "help": "Guides core DocTypes",
            "input": "single",
            "options": [
                {"label": "Operations & tracking", "value": "ops", "description": "Vehicle fleet management"},
                {"label": "Customer booking", "value": "booking", "description": "Online reservations"},
                {"label": "Reporting", "value": "reports", "description": "Fleet utilization"},
            ],
            "allow_custom": True,
        },
        "assumptions": ["Daily rate"],
        "coverage": {
            "basics": 0.17,
            "domain": 0.0,
        },
    }

    respx.post("https://api.mockllm.test/v1/chat/completions").respond(
        status_code=200,
        json={"choices": [{"message": {"content": json.dumps(turn_data)}}]},
    )

    session = OrchestratorSession(session_id="orch-sess-1")
    res = await orchestrator.handle_user_message(session, "We rent cars.")

    assert res["status"] == "needs_input"
    assert res["state"] == OrchestratorState.DISCOVERY.value
    assert res["question"] is not None
    assert res["question"]["id"] == "app_purpose"
    assert "Daily rate" in res["assumptions"]
