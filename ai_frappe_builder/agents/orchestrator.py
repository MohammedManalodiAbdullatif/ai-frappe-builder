"""
orchestrator.py — Multi-agent state machine orchestrator.
Manages session lifecycle across discovery -> drafting -> validating -> healing -> done | failed.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from ai_frappe_builder.agents.architect import ArchitectAgent, ArchitectInput
from ai_frappe_builder.agents.differ import DifferAgent, DifferInput
from ai_frappe_builder.agents.healer import HealerAgent, HealerInput
from ai_frappe_builder.agents.interviewer import InterviewerAgent, InterviewInput, InterviewTurn
from ai_frappe_builder.events import event_manager
from ai_frappe_builder.models.app_spec_v2 import AppSpecV2
from ai_frappe_builder.models.migration import migrate_v1_to_v2
from ai_frappe_builder.models.patch import SpecPatch
from ai_frappe_builder.models.validation import ValidationReport
from ai_frappe_builder.validator.rule_engine import validate_spec

logger = logging.getLogger(__name__)


class OrchestratorState(StrEnum):
    DISCOVERY = "discovery"
    DRAFTING = "drafting"
    VALIDATING = "validating"
    HEALING = "healing"
    SCRIPTING = "scripting"
    REPORTING = "reporting"
    EXPORTING = "exporting"
    TESTING = "testing"
    DONE = "done"
    FAILED = "failed"


class OrchestratorSession(BaseModel):
    """In-memory state container for an orchestrator conversation session."""

    session_id: str
    state: OrchestratorState = OrchestratorState.DISCOVERY
    archetype: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    messages: list[dict[str, str]] = Field(default_factory=list)
    spec: AppSpecV2 | None = None
    validation_report: ValidationReport | None = None
    healing_round: int = 0
    max_healing_rounds: int = 3


class Orchestrator:
    """Coordinates specialist subagents and publishes real-time lifecycle events."""

    def __init__(
        self,
        interviewer: InterviewerAgent | None = None,
        architect: ArchitectAgent | None = None,
        differ: DifferAgent | None = None,
        healer: HealerAgent | None = None,
    ) -> None:
        self.interviewer = interviewer or InterviewerAgent()
        self.architect = architect or ArchitectAgent()
        self.differ = differ or DifferAgent()
        self.healer = healer or HealerAgent()

    async def _transition(
        self,
        session: OrchestratorSession,
        new_state: OrchestratorState,
        meta: dict[str, Any] | None = None,
    ) -> None:
        old_state = session.state
        session.state = new_state
        await event_manager.publish(
            session_id=session.session_id,
            event_type="state_change",
            data={
                "from_state": old_state.value,
                "to_state": new_state.value,
                **(meta or {}),
            },
        )

    async def handle_user_message(
        self,
        session: OrchestratorSession,
        user_message: str,
        site_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Process user message and advance the state machine.
        """
        session.messages.append({"role": "user", "content": user_message})

        # Scenario 1: User requested an incremental modification to an existing spec
        if (
            session.spec
            and session.spec.app
            and session.state in (OrchestratorState.DONE, OrchestratorState.VALIDATING)
        ):
            return await self._handle_spec_mutation(session, user_message, site_context)

        # Scenario 2: Active discovery phase
        interview_input = InterviewInput(
            messages=session.messages,
            assumptions=session.assumptions,
            archetype=session.archetype,
        )

        turn: InterviewTurn = await self.interviewer.run(
            interview_input, session_id=session.session_id
        )
        if turn.archetype:
            session.archetype = turn.archetype
        if turn.assumptions_so_far:
            session.assumptions = list(dict.fromkeys(session.assumptions + turn.assumptions_so_far))

        # Check if discovery completed
        if turn.ready:
            await self._transition(session, OrchestratorState.DRAFTING)
            return await self._draft_and_validate(session, site_context)

        # Still in discovery, emit question event and reply to user
        q_data = turn.question.model_dump() if turn.question else None
        await event_manager.publish(
            session_id=session.session_id,
            event_type="question",
            data={
                "question": q_data,
                "assumptions": session.assumptions,
                "archetype": session.archetype,
            },
        )

        # Record assistant reply in messages
        assistant_reply = (
            turn.question.question if turn.question else "Please clarify your requirements."
        )
        session.messages.append({"role": "assistant", "content": assistant_reply})

        return {
            "status": "needs_input",
            "state": session.state.value,
            "response": assistant_reply,
            "question": q_data,
            "assumptions": session.assumptions,
            "archetype": session.archetype,
            "spec": session.spec.model_dump() if session.spec else None,
        }

    async def _draft_and_validate(
        self,
        session: OrchestratorSession,
        site_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Draft a fresh AppSpec from interview transcript and validate."""
        architect_input = ArchitectInput(
            transcript=session.messages,
            assumptions=session.assumptions,
            archetype=session.archetype,
        )

        spec = await self.architect.run(architect_input, session_id=session.session_id)
        session.spec = spec

        await self._transition(session, OrchestratorState.VALIDATING)
        report = validate_spec(session.spec, site_context=site_context)
        session.validation_report = report

        await event_manager.publish(
            session_id=session.session_id,
            event_type="validation",
            data=report.model_dump(),
        )

        # Self-healing loop
        while not report.is_valid and session.healing_round < session.max_healing_rounds:
            session.healing_round += 1
            await self._transition(
                session, OrchestratorState.HEALING, {"round": session.healing_round}
            )

            healer_input = HealerInput(current_spec=session.spec, validation_report=report)
            patch: SpecPatch = await self.healer.run(healer_input, session_id=session.session_id)

            if patch.operations:
                spec_dict = session.spec.model_dump()
                updated_dict = patch.apply(spec_dict)
                session.spec = migrate_v1_to_v2(updated_dict)

                await event_manager.publish(
                    session_id=session.session_id,
                    event_type="spec_patch",
                    data=patch.model_dump(),
                )

            # Re-validate
            report = validate_spec(session.spec, site_context=site_context)
            session.validation_report = report
            await event_manager.publish(
                session_id=session.session_id,
                event_type="validation",
                data=report.model_dump(),
            )

        if report.is_valid:
            await self._transition(session, OrchestratorState.DONE)
            status = "ready"
            reply = "App specification is ready and validated! You can view the data model and export the app."
        else:
            await self._transition(session, OrchestratorState.FAILED)
            status = "validation_failed"
            reply = f"Validation could not be fully resolved after {session.healing_round} healing rounds."

        session.messages.append({"role": "assistant", "content": reply})

        return {
            "status": status,
            "state": session.state.value,
            "response": reply,
            "spec": session.spec.model_dump() if session.spec else None,
            "validation": report.model_dump(),
            "assumptions": session.assumptions,
        }

    async def _handle_spec_mutation(
        self,
        session: OrchestratorSession,
        user_request: str,
        site_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Apply incremental user request to existing spec via Differ."""
        if not session.spec:
            return {"status": "error", "response": "No active spec to mutate."}

        differ_input = DifferInput(current_spec=session.spec, user_request=user_request)
        patch = await self.differ.run(differ_input, session_id=session.session_id)

        if patch.operations:
            spec_dict = session.spec.model_dump()
            updated_dict = patch.apply(spec_dict)
            session.spec = migrate_v1_to_v2(updated_dict)

            await event_manager.publish(
                session_id=session.session_id,
                event_type="spec_patch",
                data=patch.model_dump(),
            )

        report = validate_spec(session.spec, site_context=site_context)
        session.validation_report = report

        await event_manager.publish(
            session_id=session.session_id,
            event_type="validation",
            data=report.model_dump(),
        )

        reply = f"Applied patch: {patch.description}. Spec is {'valid' if report.is_valid else 'flagged with issues'}."
        session.messages.append({"role": "assistant", "content": reply})

        return {
            "status": "ready" if report.is_valid else "has_issues",
            "state": session.state.value,
            "response": reply,
            "spec": session.spec.model_dump(),
            "validation": report.model_dump(),
        }
