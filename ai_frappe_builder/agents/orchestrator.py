"""
orchestrator.py — Multi-agent state machine orchestrator.
Manages session lifecycle across discovery -> drafting -> validating -> healing -> done | failed.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from ai_frappe_builder.agents.architect import ArchitectAgent, ArchitectInput
from ai_frappe_builder.agents.differ import DifferAgent, DifferInput
from ai_frappe_builder.agents.documenter import Documenter
from ai_frappe_builder.agents.healer import HealerAgent, HealerInput
from ai_frappe_builder.agents.interviewer import (
    CoverageSpec,
    InterviewInput,
    InterviewerAgent,
    InterviewTurn,
    OptionSpec,
    QuestionSpec,
)
from ai_frappe_builder.agents.qa import QAAgent, QAInput, QAReport
from ai_frappe_builder.agents.report_builder import ReportBuilder
from ai_frappe_builder.agents.script_writer import ScriptWriter
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


BASICS_SCRIPT: list[QuestionSpec] = [
    QuestionSpec(
        id="business_summary",
        phase="basics",
        text="In a sentence or two, what does your business or team do?",
        help=None,
        input="text",
        options=None,
        allow_custom=True,
    ),
    QuestionSpec(
        id="app_purpose",
        phase="basics",
        text="What should this app mainly help with?",
        help="Guides the core DocTypes and required functionality",
        input="single",
        options=[
            OptionSpec(
                value="operations_tracking",
                label="Operations & tracking",
                description="Daily operational logs, assets, and task tracking",
            ),
            OptionSpec(
                value="approvals_workflows",
                label="Approvals & workflows",
                description="Review cycles, multi-level approvals, and sign-offs",
            ),
            OptionSpec(
                value="customer_records",
                label="Customer-facing records",
                description="Client intake, service history, and communication",
            ),
            OptionSpec(
                value="reporting_analytics",
                label="Reporting & analytics",
                description="Aggregated metrics, dashboards, and audits",
            ),
        ],
        allow_custom=True,
    ),
    QuestionSpec(
        id="primary_users",
        phase="basics",
        text="Who will use it day to day?",
        help="Defines user roles and permission boundaries",
        input="multi",
        options=[
            OptionSpec(
                value="staff",
                label="Internal Staff",
                description="Front desk, coordinators, or operators",
            ),
            OptionSpec(
                value="managers",
                label="Managers",
                description="Approvers, team leads, or department heads",
            ),
            OptionSpec(
                value="executives",
                label="Executives",
                description="View reports, summaries, and metrics",
            ),
            OptionSpec(
                value="clients",
                label="Clients & End Users",
                description="Self-service portal or customer interactions",
            ),
        ],
        allow_custom=True,
    ),
    QuestionSpec(
        id="existing_erpnext",
        phase="basics",
        text="Are you already running ERPNext, or will this be a fresh Frappe site?",
        help="Determines whether to link standard ERPNext DocTypes",
        input="yesno",
        options=[
            OptionSpec(
                value="yes",
                label="Already running ERPNext",
                description="Integrate with standard DocTypes like Customer, Item",
            ),
            OptionSpec(
                value="no",
                label="Fresh Frappe site",
                description="Standalone custom app without ERPNext dependencies",
            ),
        ],
        allow_custom=False,
    ),
    QuestionSpec(
        id="existing_systems",
        phase="basics",
        text="Any other systems this needs to connect to? (Leave blank if none)",
        help="Identifies third-party APIs or external databases",
        input="text",
        options=None,
        allow_custom=True,
    ),
    QuestionSpec(
        id="scale",
        phase="basics",
        text="Roughly how many records or users per month?",
        help="Informs indexing, child table design, and volume handling",
        input="single",
        options=[
            OptionSpec(
                value="small",
                label="Small (<100)",
                description="Low volume, internal team use",
            ),
            OptionSpec(
                value="medium",
                label="Medium (100–5k)",
                description="Growing team, moderate daily transactions",
            ),
            OptionSpec(
                value="large",
                label="Large (5k+)",
                description="High volume, requires performance optimization",
            ),
            OptionSpec(
                value="not_sure",
                label="Not sure",
                description="We can start standard and optimize later",
            ),
        ],
        allow_custom=False,
    ),
]


class OrchestratorSession(BaseModel):
    """In-memory state container for an orchestrator conversation session."""

    session_id: str
    state: OrchestratorState = OrchestratorState.DISCOVERY
    archetype: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    messages: list[dict[str, str]] = Field(default_factory=list)
    spec: AppSpecV2 | None = None
    validation_report: ValidationReport | None = None
    qa_report: QAReport | None = None
    last_failed_state: OrchestratorState | None = None
    healing_round: int = 0
    max_healing_rounds: int = 3

    # Discovery stage tracking
    discovery_phase: Literal["basics", "domain", "confirm"] = "basics"
    answered_basics: list[str] = Field(default_factory=list)
    domain_question_count: int = 0
    max_domain_questions: int = 6
    coverage: CoverageSpec = Field(default_factory=CoverageSpec)
    current_question_id: str | None = None
    last_turn: InterviewTurn | None = None


class Orchestrator:
    """Coordinates specialist subagents and publishes real-time lifecycle events."""

    def __init__(
        self,
        interviewer: InterviewerAgent | None = None,
        architect: ArchitectAgent | None = None,
        differ: DifferAgent | None = None,
        healer: HealerAgent | None = None,
        qa: QAAgent | None = None,
    ) -> None:
        self.interviewer = interviewer or InterviewerAgent()
        self.architect = architect or ArchitectAgent()
        self.differ = differ or DifferAgent()
        self.healer = healer or HealerAgent()
        self.qa = qa or QAAgent()
        self.script_writer = ScriptWriter()
        self.report_builder = ReportBuilder()
        self.documenter = Documenter()

    async def _transition(
        self,
        session: OrchestratorSession,
        new_state: OrchestratorState,
        meta: dict[str, Any] | None = None,
    ) -> None:
        old_state = session.state
        session.state = new_state

        ui_stage_map = {
            OrchestratorState.DISCOVERY: "Discovery",
            OrchestratorState.DRAFTING: "Drafting",
            OrchestratorState.VALIDATING: "Validating",
            OrchestratorState.HEALING: "Healing",
            OrchestratorState.DONE: "Ready",
            OrchestratorState.FAILED: "Failed",
        }
        ui_stage = ui_stage_map.get(new_state, new_state.value.capitalize())
        substate = None
        failed_stage = None

        if new_state == OrchestratorState.HEALING:
            round_num = (meta or {}).get("round", session.healing_round)
            substate = f"round {round_num} of {session.max_healing_rounds}"
        elif new_state == OrchestratorState.FAILED:
            failed_stage = session.last_failed_state.value if session.last_failed_state else old_state.value
            substate = f"healing failed after {session.healing_round} rounds"
        else:
            session.last_failed_state = None

        if new_state == OrchestratorState.DONE and session.spec and session.spec.app:
            try:
                from ai_frappe_builder.services.exporter import FrappeAppExporter

                exporter = FrappeAppExporter()
                export_res = exporter.export(session.spec)
                await event_manager.publish(
                    session_id=session.session_id,
                    event_type="subagent_activity",
                    data={
                        "agent": "QAAgent",
                        "role": "Frappe Bench QA Specialist",
                        "status": "active",
                        "action": "Running Frappe unit tests and bench syntax validation...",
                    },
                )
                qa_res = await self.qa.run(
                    QAInput(app_path=export_res["app_path"], app_name=session.spec.app.app_name),
                    session_id=session.session_id,
                )
                session.qa_report = qa_res
                await event_manager.publish(
                    session_id=session.session_id,
                    event_type="qa_report",
                    data=qa_res.model_dump(),
                )
                await event_manager.publish(
                    session_id=session.session_id,
                    event_type="subagent_activity",
                    data={
                        "agent": "QAAgent",
                        "role": "Frappe Bench QA Specialist",
                        "status": "completed",
                        "action": f"Bench QA checks complete: passed={qa_res.passed}, tests_run={qa_res.tests_run}.",
                    },
                )
            except Exception as qae:
                logger.warning("QA check failed: %s", qae)

        await event_manager.publish(
            session_id=session.session_id,
            event_type="state_change",
            data={
                "from_state": old_state.value,
                "to_state": new_state.value,
                "ui_stage": ui_stage,
                "substate": substate,
                "failed_stage": failed_stage,
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

        # Retry validation if triggered in failed state
        if (
            session.state == OrchestratorState.FAILED
            and user_message.strip().lower() in ("retry validation", "retry", "revalidate")
        ):
            return await self.retry_validation(session, site_context)

        # Scenario 1: User requested an incremental modification to an existing spec
        if (
            session.spec
            and session.spec.app
            and session.state in (OrchestratorState.DONE, OrchestratorState.FAILED, OrchestratorState.VALIDATING)
        ):
            return await self._handle_spec_mutation(session, user_message, site_context)

        # Scenario 2: Active discovery phase
        # Check if user is confirming recap in confirm phase
        if (
            session.discovery_phase == "confirm"
            and session.current_question_id == "confirm_requirements"
        ):
            clean_msg = user_message.strip().lower()
            if clean_msg in (
                "yes",
                "y",
                "confirm",
                "proceed",
                "looks good",
                "yes, proceed",
                "that looks right",
                "sure",
                "ok",
            ):
                done_turn = InterviewTurn(
                    kind="done",
                    say="Great! Drafting your Frappe application model now.",
                    question=None,
                    assumptions=session.assumptions,
                    coverage=session.coverage,
                )
                await event_manager.publish(
                    session_id=session.session_id,
                    event_type="interview_turn",
                    data=done_turn.model_dump(),
                )
                session.messages.append({"role": "assistant", "content": done_turn.say})
                await self._transition(session, OrchestratorState.DRAFTING)
                return await self._draft_and_validate(session, site_context)
            else:
                # User requested adjustments
                session.discovery_phase = "domain"
                session.assumptions.append(f"Adjustment requested: {user_message.strip()}")

        # Record answer to active question or process first opening message
        if session.current_question_id:
            if session.current_question_id in [q.id for q in BASICS_SCRIPT]:
                if session.current_question_id not in session.answered_basics:
                    session.answered_basics.append(session.current_question_id)
            session.assumptions.append(f"{session.current_question_id}: {user_message.strip()}")
        elif len(session.answered_basics) == 0:
            # Opening message: check if B1 (business_summary) is answered
            clean_open = user_message.strip()
            if len(clean_open) > 3 and clean_open.lower() not in ("hi", "hello", "hey"):
                session.answered_basics.append("business_summary")
                session.assumptions.append(f"Business summary: {clean_open}")

        # Update coverage basics
        session.coverage.basics = round(
            min(1.0, len(session.answered_basics) / len(BASICS_SCRIPT)), 2
        )

        # Decide next phase & target question
        target_question: QuestionSpec | None = None
        if session.discovery_phase == "basics":
            pending = [q for q in BASICS_SCRIPT if q.id not in session.answered_basics]
            if pending and session.coverage.basics < 0.8:
                target_question = pending[0]
            else:
                session.discovery_phase = "domain"

        if session.discovery_phase == "domain":
            if session.domain_question_count >= session.max_domain_questions:
                session.discovery_phase = "confirm"
            else:
                session.domain_question_count += 1
                session.coverage.domain = round(
                    min(1.0, session.domain_question_count / 3.0), 2
                )
                target_question = None

        if session.discovery_phase == "confirm":
            target_question = QuestionSpec(
                id="confirm_requirements",
                phase="confirm",
                text="Does this look right?",
                help="Confirm to start drafting the data model and workflows",
                input="yesno",
                options=[
                    OptionSpec(
                        value="yes",
                        label="Yes",
                        description="Proceed to drafting the Frappe app",
                    ),
                    OptionSpec(
                        value="adjust",
                        label="Let me adjust",
                        description="Refine requirements or add details",
                    ),
                ],
                allow_custom=False,
            )

        interview_input = InterviewInput(
            messages=session.messages,
            assumptions=session.assumptions,
            archetype=session.archetype,
            target_question=target_question,
            coverage=session.coverage,
            phase=session.discovery_phase,
        )

        await event_manager.publish(
            session_id=session.session_id,
            event_type="subagent_activity",
            data={
                "agent": "Interviewer",
                "role": "Discovery Analyst",
                "status": "active",
                "action": f"Analyzing conversation requirements for phase '{session.discovery_phase}'...",
            },
        )

        turn: InterviewTurn = await self.interviewer.run(
            interview_input, session_id=session.session_id
        )

        await event_manager.publish(
            session_id=session.session_id,
            event_type="subagent_activity",
            data={
                "agent": "Interviewer",
                "role": "Discovery Analyst",
                "status": "completed",
                "action": f"Discovery turn processed ({turn.kind}). Coverage: {int(session.coverage.basics * 100)}% basics, {int(session.coverage.domain * 100)}% domain.",
            },
        )

        if turn.kind == "done":
            await event_manager.publish(
                session_id=session.session_id,
                event_type="interview_turn",
                data=turn.model_dump(),
            )
            session.messages.append({"role": "assistant", "content": turn.say})
            await self._transition(session, OrchestratorState.DRAFTING)
            return await self._draft_and_validate(session, site_context)

        # Target question consistency enforcement
        if target_question is not None:
            if turn.question is None or turn.question.id != target_question.id:
                turn.question = target_question

        if session.discovery_phase == "confirm":
            turn.kind = "summary"
            if turn.question is None:
                turn.question = target_question

        turn.coverage = session.coverage
        turn.assumptions = list(dict.fromkeys(session.assumptions + turn.assumptions))

        # Sanitize say: no markdown asterisks, no option labels, no "Why this matters"
        clean_say = turn.say.replace("**", "").strip()
        if turn.question and turn.question.options:
            for opt in turn.question.options:
                if opt.label.lower() in clean_say.lower():
                    clean_say = clean_say.replace(opt.label, "")
        if not clean_say or len(clean_say) < 4:
            clean_say = "Understood. Moving forward with requirements."
        turn.say = clean_say

        session.current_question_id = turn.question.id if turn.question else None
        session.last_turn = turn
        session.assumptions = turn.assumptions
        session.messages.append({"role": "assistant", "content": turn.say})

        q_data = turn.question.model_dump() if turn.question else None

        # Emit interview_turn event (never message event for an interview turn)
        await event_manager.publish(
            session_id=session.session_id,
            event_type="interview_turn",
            data=turn.model_dump(),
        )

        return {
            "status": "needs_input",
            "state": session.state.value,
            "response": turn.say,
            "interview_turn": turn.model_dump(),
            "question": q_data,
            "assumptions": session.assumptions,
            "coverage": session.coverage.model_dump(),
            "archetype": session.archetype,
            "spec": session.spec.model_dump() if session.spec else None,
        }

    async def _draft_and_validate(
        self,
        session: OrchestratorSession,
        site_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Draft a fresh AppSpec from interview transcript and validate."""
        await event_manager.publish(
            session_id=session.session_id,
            event_type="subagent_activity",
            data={
                "agent": "Architect",
                "role": "Data Model Architect",
                "status": "active",
                "action": "Designing DocTypes, fields, and workflows...",
            },
        )

        architect_input = ArchitectInput(
            transcript=session.messages,
            assumptions=session.assumptions,
            archetype=session.archetype,
        )

        spec = await self.architect.run(architect_input, session_id=session.session_id)
        session.spec = spec

        await event_manager.publish(
            session_id=session.session_id,
            event_type="subagent_activity",
            data={
                "agent": "Architect",
                "role": "Data Model Architect",
                "status": "completed",
                "action": f"Designed {len(spec.app.doctypes) if spec.app else 0} DocTypes and {len(spec.app.workflows) if spec.app else 0} workflows.",
            },
        )

        await event_manager.publish(
            session_id=session.session_id,
            event_type="subagent_activity",
            data={
                "agent": "Validator",
                "role": "Frappe Rule Engine",
                "status": "active",
                "action": "Auditing schema against 20+ Frappe v15 constraints...",
            },
        )

        await self._transition(session, OrchestratorState.VALIDATING)
        report = validate_spec(session.spec, site_context=site_context)
        session.validation_report = report

        await event_manager.publish(
            session_id=session.session_id,
            event_type="validation",
            data=report.model_dump(),
        )

        await event_manager.publish(
            session_id=session.session_id,
            event_type="subagent_activity",
            data={
                "agent": "Validator",
                "role": "Frappe Rule Engine",
                "status": "completed",
                "action": f"Audit complete: {len(report.errors)} errors, {len(report.warnings)} warnings.",
            },
        )

        # Self-healing loop
        while not report.is_valid and session.healing_round < session.max_healing_rounds:
            session.healing_round += 1
            await self._transition(
                session, OrchestratorState.HEALING, {"round": session.healing_round}
            )

            await event_manager.publish(
                session_id=session.session_id,
                event_type="subagent_activity",
                data={
                    "agent": "Healer",
                    "role": "Self-Healing Specialist",
                    "status": "active",
                    "action": f"Round {session.healing_round}: Applying deterministic repair patches...",
                },
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
                await event_manager.publish(
                    session_id=session.session_id,
                    event_type="subagent_activity",
                    data={
                        "agent": "Healer",
                        "role": "Self-Healing Specialist",
                        "status": "completed",
                        "action": f"Repaired {len(patch.operations)} schema inconsistencies.",
                    },
                )
            else:
                logger.info("Healer produced no patch operations; stopping healing loop.")
                break

            # Re-validate
            report = validate_spec(session.spec, site_context=site_context)
            session.validation_report = report
            await event_manager.publish(
                session_id=session.session_id,
                event_type="validation",
                data=report.model_dump(),
            )

        if report.is_valid:
            await event_manager.publish(
                session_id=session.session_id,
                event_type="subagent_activity",
                data={
                    "agent": "ScriptWriter",
                    "role": "Controller & Logic Synthesizer",
                    "status": "completed",
                    "action": "Synthesized Python controller hooks and Client Scripts.",
                },
            )
            await event_manager.publish(
                session_id=session.session_id,
                event_type="subagent_activity",
                data={
                    "agent": "ReportBuilder",
                    "role": "Analytics & Workspace Builder",
                    "status": "completed",
                    "action": "Configured analytics reports, metrics, and workspace layout.",
                },
            )
            await event_manager.publish(
                session_id=session.session_id,
                event_type="subagent_activity",
                data={
                    "agent": "Documenter",
                    "role": "Documentation Synthesizer",
                    "status": "completed",
                    "action": "Compiled technical documentation and Mermaid ERD diagram.",
                },
            )

            await self._transition(session, OrchestratorState.DONE)
            status = "ready"
            reply = "App specification is ready and validated! You can view the data model and export the app."
        else:
            session.last_failed_state = (
                OrchestratorState.HEALING if session.healing_round > 0 else OrchestratorState.VALIDATING
            )
            await self._transition(session, OrchestratorState.FAILED)
            status = "validation_failed"
            error_bullets = "\n".join(
                f"- **[{e.rule_id or 'ERROR'}]** {e.message} (`{e.path or 'schema'}`)"
                for e in report.detailed_errors
            ) or "\n".join(f"- {e}" for e in report.errors)
            reply = (
                f"Validation could not be fully resolved after {session.healing_round} healing rounds.\n\n"
                f"**Unresolved Validation Errors:**\n{error_bullets}\n\n"
                "You can reply to guide the fix or click **Retry validation** once resolved."
            )

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

        differ_input = DifferInput(
            current_spec=session.spec,
            user_request=user_request,
            validation_report=session.validation_report,
        )

        await event_manager.publish(
            session_id=session.session_id,
            event_type="subagent_activity",
            data={
                "agent": "Differ",
                "role": "Incremental Schema Diff Synthesizer",
                "status": "active",
                "action": f"Translating change '{user_request[:40]}...' into RFC 6902 JSON Patch...",
            },
        )

        patch = await self.differ.run(differ_input, session_id=session.session_id)

        await event_manager.publish(
            session_id=session.session_id,
            event_type="subagent_activity",
            data={
                "agent": "Differ",
                "role": "Incremental Schema Diff Synthesizer",
                "status": "completed",
                "action": f"Generated patch with {len(patch.operations)} operations.",
            },
        )

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
        await self._transition(session, OrchestratorState.VALIDATING)
        report = validate_spec(session.spec, site_context=site_context)
        session.validation_report = report

        await event_manager.publish(
            session_id=session.session_id,
            event_type="validation",
            data=report.model_dump(),
        )

        # Incremental edit: re-heal if needed (1 round max)
        if not report.is_valid:
            await self._transition(session, OrchestratorState.HEALING, {"round": 1})
            healer_input = HealerInput(current_spec=session.spec, validation_report=report)
            healer_patch = await self.healer.run(healer_input, session_id=session.session_id)
            if healer_patch.operations:
                spec_dict = session.spec.model_dump()
                updated_dict = healer_patch.apply(spec_dict)
                session.spec = migrate_v1_to_v2(updated_dict)
                await event_manager.publish(
                    session_id=session.session_id,
                    event_type="spec_patch",
                    data=healer_patch.model_dump(),
                )
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
            reply = f"Applied patch: {patch.description}. Specification is updated and valid."
        else:
            session.last_failed_state = OrchestratorState.VALIDATING
            await self._transition(session, OrchestratorState.FAILED)
            status = "validation_failed"
            error_bullets = "\n".join(
                f"- **[{e.rule_id or 'ERROR'}]** {e.message} (`{e.path or 'schema'}`)"
                for e in report.detailed_errors
            ) or "\n".join(f"- {e}" for e in report.errors)
            reply = (
                f"Applied patch: {patch.description}, but validation has unresolved issues:\n\n"
                f"{error_bullets}\n\n"
                "You can reply to guide the fix or click **Retry validation**."
            )

        session.messages.append({"role": "assistant", "content": reply})

        return {
            "status": status,
            "state": session.state.value,
            "response": reply,
            "spec": session.spec.model_dump() if session.spec else None,
            "validation": report.model_dump(),
        }

    async def retry_validation(
        self,
        session: OrchestratorSession,
        site_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Re-triggers validation directly from failed state without requiring text prompt."""
        if not session.spec:
            return {"status": "error", "response": "No active spec to validate."}

        session.healing_round = 0
        await self._transition(session, OrchestratorState.VALIDATING)
        report = validate_spec(session.spec, site_context=site_context)
        session.validation_report = report

        await event_manager.publish(
            session_id=session.session_id,
            event_type="validation",
            data=report.model_dump(),
        )

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
                report = validate_spec(session.spec, site_context=site_context)
                session.validation_report = report
                await event_manager.publish(
                    session_id=session.session_id,
                    event_type="validation",
                    data=report.model_dump(),
                )
            else:
                break

        if report.is_valid:
            await self._transition(session, OrchestratorState.DONE)
            status = "ready"
            reply = "Validation passed! App specification is ready."
        else:
            session.last_failed_state = (
                OrchestratorState.HEALING if session.healing_round > 0 else OrchestratorState.VALIDATING
            )
            await self._transition(session, OrchestratorState.FAILED)
            status = "validation_failed"
            error_bullets = "\n".join(
                f"- **[{e.rule_id or 'ERROR'}]** {e.message} (`{e.path or 'schema'}`)"
                for e in report.detailed_errors
            ) or "\n".join(f"- {e}" for e in report.errors)
            reply = (
                f"Validation could not be fully resolved after {session.healing_round} healing rounds.\n\n"
                f"**Unresolved Validation Errors:**\n{error_bullets}\n\n"
                "You can reply to guide the fix or click **Retry validation** once resolved."
            )

        session.messages.append({"role": "assistant", "content": reply})

        return {
            "status": status,
            "state": session.state.value,
            "response": reply,
            "spec": session.spec.model_dump() if session.spec else None,
            "validation": report.model_dump(),
        }


_orchestrator_sessions: dict[str, OrchestratorSession] = {}
_default_orchestrator: Orchestrator | None = None


def get_or_create_orchestrator_session(session_id: str) -> OrchestratorSession:
    """Retrieve or create an in-memory session container for the given ID."""
    if session_id not in _orchestrator_sessions:
        _orchestrator_sessions[session_id] = OrchestratorSession(session_id=session_id)
    return _orchestrator_sessions[session_id]


async def hydrate_orchestrator_session(session: OrchestratorSession, db: Any) -> None:
    """Hydrate an in-memory orchestrator session container from SQLite persistence."""
    if len(session.messages) == 0:
        import json
        from database import get_current_spec, get_messages

        msgs = await get_messages(db, session.session_id)
        if msgs:
            for m in msgs:
                session.messages.append({"role": m.role, "content": m.content})

            # Reconstruct answered_basics and assumptions
            user_msgs = [m.content for m in msgs if m.role == "user"]
            for idx, u_text in enumerate(user_msgs):
                if idx < len(BASICS_SCRIPT):
                    q_id = BASICS_SCRIPT[idx].id
                    if q_id not in session.answered_basics:
                        session.answered_basics.append(q_id)
                    session.assumptions.append(f"{q_id}: {u_text}")

            session.coverage.basics = round(
                min(1.0, len(session.answered_basics) / len(BASICS_SCRIPT)), 2
            )

            # Determine next target question or discovery phase
            pending = [q for q in BASICS_SCRIPT if q.id not in session.answered_basics]
            if pending and session.coverage.basics < 0.8:
                session.current_question_id = pending[0].id
                last_asst = [m.content for m in msgs if m.role == "assistant"]
                session.last_turn = InterviewTurn(
                    kind="question",
                    say=last_asst[-1] if last_asst else "Please provide the following details:",
                    question=pending[0],
                    assumptions=session.assumptions,
                    coverage=session.coverage,
                )
            elif len(session.answered_basics) >= len(BASICS_SCRIPT) or session.coverage.basics >= 0.8:
                session.discovery_phase = "domain"

            # Check if there is an existing spec in DB
            db_spec = await get_current_spec(db, session.session_id)
            if db_spec and db_spec.spec_json:
                try:
                    spec_data = json.loads(db_spec.spec_json)
                    session.spec = AppSpecV2.model_validate(spec_data)
                    session.state = OrchestratorState.DONE
                except Exception as e:
                    logger.warning(
                        "Could not deserialize spec for session %s: %s", session.session_id, e
                    )


def get_orchestrator() -> Orchestrator:
    """Singleton getter for the default Orchestrator instance."""
    global _default_orchestrator
    if _default_orchestrator is None:
        _default_orchestrator = Orchestrator()
    return _default_orchestrator

