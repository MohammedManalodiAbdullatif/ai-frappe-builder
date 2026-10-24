"""
interviewer.py — Discovery interviewer subagent.
Asks questions one at a time with actionable choices, identifies business archetypes,
records explicit assumptions, and signals when requirements are ready for architecture.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from ai_frappe_builder.agents.base import BaseAgent
from ai_frappe_builder.models.app_spec_v2 import InterviewQuestion

logger = logging.getLogger(__name__)


class InterviewInput(BaseModel):
    """Input payload to the Interviewer agent."""

    messages: list[dict[str, str]] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    archetype: str | None = None


class InterviewTurn(BaseModel):
    """Output turn produced by the Interviewer agent."""

    archetype: str | None = None
    assumptions_so_far: list[str] = Field(default_factory=list)
    ready: bool = False
    question: InterviewQuestion | None = None


class InterviewerAgent(BaseAgent[InterviewInput, InterviewTurn]):
    """Conducts interactive discovery one question at a time."""

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

        # Provide context of existing assumptions and archetype
        context_notes = []
        if input_data.archetype:
            context_notes.append(f"Current detected archetype: {input_data.archetype}")
        if input_data.assumptions:
            context_notes.append(f"Assumptions accumulated so far: {input_data.assumptions}")
        if context_notes:
            prompt_messages.append({"role": "system", "content": "\n".join(context_notes)})

        # Append conversation messages
        prompt_messages.extend(input_data.messages)

        raw_output = await self.llm_client.complete(
            messages=prompt_messages,
            response_schema=self.output_model,
            stream_callback=stream_callback,
            agent_name=self.name,
            session_id=session_id,
            temperature=0.2,
        )

        if isinstance(raw_output, dict):
            return self.output_model.model_validate(raw_output)
        return self.output_model()
