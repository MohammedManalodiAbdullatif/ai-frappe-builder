"""
healer.py — Automated schema error repair subagent.
Emits targeted RFC 6902 SpecPatches to fix deterministic validation errors.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel

from ai_frappe_builder.agents.base import BaseAgent
from ai_frappe_builder.models.app_spec_v2 import AppSpecV2
from ai_frappe_builder.models.patch import SpecPatch
from ai_frappe_builder.models.validation import ValidationReport

logger = logging.getLogger(__name__)


class HealerInput(BaseModel):
    """Input payload to Healer agent."""

    current_spec: AppSpecV2
    validation_report: ValidationReport


class HealerAgent(BaseAgent[HealerInput, SpecPatch]):
    """Repairs schema validation errors with minimal surgical JSON Patches."""

    name = "healer"
    output_model = SpecPatch

    async def run(
        self,
        input_data: HealerInput,
        session_id: str | None = None,
        stream_callback: Any | None = None,
    ) -> SpecPatch:
        spec_dump = input_data.current_spec.model_dump(exclude_none=True)
        report_dump = input_data.validation_report.model_dump(exclude_none=True)

        prompt_messages: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": (
                    f"Current AppSpec:\n```json\n{json.dumps(spec_dump, indent=2)}\n```\n\n"
                    f"Validation Failures & Fix Hints:\n```json\n{json.dumps(report_dump, indent=2)}\n```\n\n"
                    "Generate minimal RFC 6902 JSON patch operations to fix all validation errors."
                ),
            },
        ]

        raw_output = await self.llm_client.complete(
            messages=prompt_messages,
            response_schema=self.output_model,
            stream_callback=stream_callback,
            agent_name=self.name,
            session_id=session_id,
            temperature=0.1,
        )

        if isinstance(raw_output, dict):
            return SpecPatch.model_validate(raw_output)
        return SpecPatch(description="Empty repair patch")
