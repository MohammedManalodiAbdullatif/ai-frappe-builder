"""
architect.py — AppSpec 2.0 generation specialist subagent.
Synthesizes discovery requirements into a fully articulated Frappe app specification.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from ai_frappe_builder.agents.base import BaseAgent
from ai_frappe_builder.models.app_spec_v2 import AppSpecV2
from ai_frappe_builder.models.migration import migrate_v1_to_v2, normalize_workflows

logger = logging.getLogger(__name__)


class ArchitectInput(BaseModel):
    """Input requirements and interview history for architecture generation."""

    transcript: list[dict[str, str]] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    archetype: str | None = None


class ArchitectAgent(BaseAgent[ArchitectInput, AppSpecV2]):
    """Converts business requirements into AppSpec 2.0."""

    name = "architect"
    output_model = AppSpecV2

    async def run(
        self,
        input_data: ArchitectInput,
        session_id: str | None = None,
        stream_callback: Any | None = None,
    ) -> AppSpecV2:
        prompt_messages: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt},
        ]

        context_notes = [
            f"Archetype: {input_data.archetype or 'custom'}",
            f"Explicit assumptions: {input_data.assumptions}",
        ]
        prompt_messages.append({"role": "system", "content": "\n".join(context_notes)})
        prompt_messages.extend(input_data.transcript)

        user_prompt = (
            "Generate the complete, idiomatic Frappe v15 AppSpec 2.0 based on the discovered requirements. "
            "Reuse standard ERPNext doctypes where applicable, create child tables with istable=1, "
            "set Title Case for doctype names, lowercase snake_case for fieldnames, and full System Manager permissions."
        )
        prompt_messages.append({"role": "user", "content": user_prompt})

        raw_output = await self.llm_client.complete(
            messages=prompt_messages,
            response_schema=self.output_model,
            stream_callback=stream_callback,
            agent_name=self.name,
            session_id=session_id,
            temperature=0.1,
        )

        if isinstance(raw_output, dict):
            # Normalize via migration if necessary
            spec = migrate_v1_to_v2(raw_output)
        elif isinstance(raw_output, AppSpecV2):
            spec = raw_output
        else:
            return AppSpecV2(status="failed")

        return normalize_workflows(spec)
