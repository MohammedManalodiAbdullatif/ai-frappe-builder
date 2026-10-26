"""
differ.py — Incremental specification patcher subagent.
Emits minimal RFC 6902 JSON Patches for natural-language user change requests.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel

from ai_frappe_builder.agents.base import BaseAgent
from ai_frappe_builder.models.app_spec_v2 import AppSpecV2
from ai_frappe_builder.models.patch import PatchOperation, SpecPatch
from ai_frappe_builder.models.validation import ValidationReport

logger = logging.getLogger(__name__)


class DifferInput(BaseModel):
    """Input payload to Differ agent."""

    current_spec: AppSpecV2
    user_request: str
    validation_report: ValidationReport | None = None


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
        # Check for deterministic single field addition
        req = input_data.user_request.strip()
        add_field_match = re.search(
            r"add (?:an? )?([a-z0-9_]+) ([a-zA-Z]+) field to ([A-Za-z0-9 ]+)",
            req,
            re.IGNORECASE,
        )
        if add_field_match and input_data.current_spec.app:
            fname = add_field_match.group(1).lower()
            ftype_raw = add_field_match.group(2).capitalize()
            valid_types = {
                "Date": "Date",
                "Data": "Data",
                "Int": "Int",
                "Currency": "Currency",
                "Float": "Float",
                "Text": "Text",
                "Check": "Check",
                "Datetime": "Datetime",
            }
            ftype = valid_types.get(ftype_raw, ftype_raw)
            dt_name = add_field_match.group(3).strip()
            dt_idx = next(
                (
                    i
                    for i, d in enumerate(input_data.current_spec.app.doctypes)
                    if d.name.lower() == dt_name.lower()
                ),
                None,
            )
            if dt_idx is not None:
                flabel = " ".join(word.capitalize() for word in fname.split("_"))
                new_field = {
                    "fieldname": fname,
                    "label": flabel,
                    "fieldtype": ftype,
                    "reqd": False,
                }
                return SpecPatch(
                    description=f"Add {fname} field to {input_data.current_spec.app.doctypes[dt_idx].name}",
                    operations=[
                        PatchOperation(
                            op="add",
                            path=f"/app/doctypes/{dt_idx}/fields/-",
                            value=new_field,
                        )
                    ],
                )

        spec_dump = input_data.current_spec.model_dump(exclude_none=True)
        compact_spec = json.dumps(spec_dump, indent=2)

        report_context = ""
        if input_data.validation_report and input_data.validation_report.errors:
            report_dump = input_data.validation_report.model_dump(exclude_none=True)
            report_context = (
                f"\n\nCurrent Validation Errors to Resolve:\n```json\n"
                f"{json.dumps(report_dump, indent=2)}\n```\n"
            )

        prompt_messages: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": (
                    f"Current AppSpec:\n```json\n{compact_spec}\n```\n\n"
                    f'User Change Request:\n"{input_data.user_request}"\n'
                    f"{report_context}\n"
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
