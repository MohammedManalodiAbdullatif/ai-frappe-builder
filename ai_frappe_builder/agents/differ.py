"""
differ.py — Incremental specification patcher subagent.
Emits minimal RFC 6902 JSON Patches for natural-language user change requests.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel

from ai_frappe_builder.agents.base import BaseAgent
from ai_frappe_builder.models.app_spec_v2 import AppSpecV2
from ai_frappe_builder.models.patch import SpecPatch

logger = logging.getLogger(__name__)


class DifferInput(BaseModel):
    """Input payload to Differ agent."""

    current_spec: AppSpecV2
    user_request: str


class DifferAgent(BaseAgent[DifferInput, SpecPatch]):
    """Produces minimal RFC 6902 SpecPatch modifying an existing spec."""

    name = "differ"
    output_model = SpecPatch

    async def run(
        self,
        input_data: DifferInput,
        session_id: str | None = None,
        stream_callback: Any | None = None,
    ) -> SpecPatch:
        spec_dump = input_data.current_spec.model_dump(exclude_none=True)
        # Prune spec dump if very large, but keep app structure
        compact_spec = json.dumps(spec_dump, indent=2)

        prompt_messages: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": (
                    f"Current AppSpec:\n```json\n{compact_spec}\n```\n\n"
                    f'User Change Request:\n"{input_data.user_request}"\n\n'
                    "Synthesize the minimal RFC 6902 JSON patch operations to apply this change."
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
        return SpecPatch(description="Empty patch")
