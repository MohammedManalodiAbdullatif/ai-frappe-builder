"""
interviewer.py — Discovery interviewer subagent.
Asks structured questions one at a time, identifies business requirements,
records explicit assumptions, and signals when requirements are ready for architecture.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ai_frappe_builder.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class OptionSpec(BaseModel):
    """Actionable option choice for single/multi questions."""

    model_config = ConfigDict(extra="forbid")

    value: str
    label: str
    description: str | None = None


class QuestionSpec(BaseModel):
    """Structured question definition."""

    model_config = ConfigDict(extra="forbid")

    id: str
    phase: Literal["basics", "domain", "confirm"]
    text: str
    help: str | None = None
    input: Literal["single", "multi", "text", "yesno"]
    options: list[OptionSpec] | None = None
    allow_custom: bool = False


class CoverageSpec(BaseModel):
    """Tracks requirement discovery coverage per phase."""

    model_config = ConfigDict(extra="forbid")

    basics: float = Field(default=0.0, ge=0.0, le=1.0)
    domain: float = Field(default=0.0, ge=0.0, le=1.0)


class InterviewTurn(BaseModel):
    """Output turn produced by the Interviewer agent. Strict Pydantic model."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["question", "summary", "done"]
    say: str
    question: QuestionSpec | None = None
    assumptions: list[str] = Field(default_factory=list)
    coverage: CoverageSpec = Field(default_factory=CoverageSpec)

    @property
    def ready(self) -> bool:
        return self.kind == "done"


class InterviewInput(BaseModel):
    """Input payload to the Interviewer agent."""

    messages: list[dict[str, str]] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    archetype: str | None = None
    target_question: QuestionSpec | None = None
    coverage: CoverageSpec = Field(default_factory=CoverageSpec)
    phase: Literal["basics", "domain", "confirm"] = "basics"


class InterviewerAgent(BaseAgent[InterviewInput, InterviewTurn]):
    """Conducts interactive discovery one structured question at a time."""

    name = "interviewer"
    output_model = InterviewTurn

    async def run(
        self,
        input_data: InterviewInput,
        session_id: str | None = None,
        stream_callback: Any | None = None,
    ) -> InterviewTurn:
        prompt_messages: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt},
        ]

        target_question = input_data.target_question
        effective_phase = input_data.phase
        effective_coverage = input_data.coverage

        # Check if this is opening message with business description (e.g. "clinic with 3 branches")
        first_msg = (
            input_data.messages[0].get("content", "").strip()
            if input_data.messages
            else ""
        )
        if (
            target_question is None
            and len(input_data.messages) == 1
            and len(first_msg) > 3
            and first_msg.lower() not in ("hi", "hello", "hey")
        ):
            # B1 is answered by opening message, skip to B2 app_purpose
            target_question = QuestionSpec(
                id="app_purpose",
                phase="basics",
                text="What should this app mainly help with?",
                help="Guides the core DocTypes and required functionality",
                input="single",
                options=[
                    OptionSpec(
                        value="operations_tracking",
                        label="Operations & tracking",
                        description="Daily operational logs, assets, and patient tracking",
                    ),
                    OptionSpec(
                        value="approvals_workflows",
                        label="Approvals & workflows",
                        description="Review cycles, prescription approvals, and sign-offs",
                    ),
                    OptionSpec(
                        value="customer_records",
                        label="Customer-facing records",
                        description="Patient intake records, medical history, and communications",
                    ),
                    OptionSpec(
                        value="reporting_analytics",
                        label="Reporting & analytics",
                        description="Aggregated clinic metrics, doctor workload, and visit counts",
                    ),
                ],
                allow_custom=True,
            )
            effective_phase = "basics"
            effective_coverage = CoverageSpec(basics=0.17, domain=0.0)

        # Context notes for phase, coverage, assumptions, target question
        context_notes: list[str] = [
            f"Current Discovery Phase: {effective_phase}",
            f"Coverage so far: basics={effective_coverage.basics:.2f}, domain={effective_coverage.domain:.2f}",
        ]
        if input_data.archetype:
            context_notes.append(f"Detected business archetype: {input_data.archetype}")
        if input_data.assumptions:
            context_notes.append(f"Assumptions accumulated so far: {input_data.assumptions}")
        if target_question:
            context_notes.append(
                f"Next scripted question to tailor or confirm: {target_question.model_dump_json()}"
            )

        prompt_messages.append({"role": "system", "content": "\n".join(context_notes)})
        prompt_messages.extend(input_data.messages)

        turn: InterviewTurn
        try:
            raw_output = await self.llm_client.complete(
                messages=prompt_messages,
                response_schema=self.output_model,
                stream_callback=stream_callback,
                agent_name=self.name,
                session_id=session_id,
                temperature=0.2,
            )
            if isinstance(raw_output, dict):
                turn = self.output_model.model_validate(raw_output)
            elif isinstance(raw_output, self.output_model):
                turn = raw_output
            else:
                raise ValueError(f"Unexpected output type: {type(raw_output)}")
        except Exception as exc:
            logger.warning(
                "Interviewer completion failed validation: %s. Retrying once with error prompt...",
                exc,
            )
            retry_messages = list(prompt_messages) + [
                {
                    "role": "user",
                    "content": (
                        f"Your previous response failed schema validation: {exc}.\n"
                        "Please fix the format and return strictly valid JSON matching the InterviewTurn schema. "
                        "Do not include unknown keys. Output JSON only."
                    ),
                }
            ]
            try:
                raw_retry = await self.llm_client.complete(
                    messages=retry_messages,
                    response_schema=self.output_model,
                    agent_name=self.name,
                    session_id=session_id,
                    temperature=0.0,
                )
                if isinstance(raw_retry, dict):
                    turn = self.output_model.model_validate(raw_retry)
                elif isinstance(raw_retry, self.output_model):
                    turn = raw_retry
                else:
                    raise ValueError(f"Unexpected retry output type: {type(raw_retry)}")
            except Exception as retry_err:
                logger.error(
                    "Interviewer retry failed: %s. Falling back to kind='question', input='text'.",
                    retry_err,
                )
                turn = InterviewTurn(
                    kind="question",
                    say="Could you tell me a bit more about your requirements?",
                    question=target_question
                    or QuestionSpec(
                        id="clarify_requirements",
                        phase=effective_phase,
                        text="Could you describe your app requirements in more detail?",
                        help=None,
                        input="text",
                        options=None,
                        allow_custom=True,
                    ),
                    assumptions=input_data.assumptions,
                    coverage=effective_coverage,
                )

        # Enforce target question consistency if explicitly provided in input_data,
        # or if LLM didn't return a question
        if input_data.target_question is not None:
            if turn.question is None or turn.question.id != input_data.target_question.id:
                turn.question = input_data.target_question
        elif turn.question is None and target_question is not None:
            turn.question = target_question

        # Enforce gate: domain phase must not start before basics coverage >= 0.8
        if turn.coverage.basics < 0.8 and turn.question and turn.question.phase == "domain":
            turn.question.phase = "basics"

        # Sanitize turn.say: no markdown asterisks, no option labels, no "Why this matters"
        clean_say = turn.say.replace("**", "").strip()
        if turn.question and turn.question.options:
            for opt in turn.question.options:
                if opt.label.lower() in clean_say.lower():
                    clean_say = clean_say.replace(opt.label, "")
        if "why this matters" in clean_say.lower():
            clean_say = clean_say.split("Why this matters")[0].strip()
        if not clean_say or len(clean_say) < 4:
            clean_say = "Understood. Let's move to the next detail."
        turn.say = clean_say

        return turn
