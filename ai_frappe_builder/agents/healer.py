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
from ai_frappe_builder.models.app_spec_v2 import (
    AppSpecV2,
    FieldSpec,
    PermissionSpec,
    WorkflowState,
    WorkflowTransition,
)
from ai_frappe_builder.models.patch import SpecPatch, make_spec_patch
from ai_frappe_builder.models.validation import ValidationReport

logger = logging.getLogger(__name__)


def heal_workflow_errors(spec: AppSpecV2, report: ValidationReport) -> SpecPatch:
    """
    Synthesize RFC 6902 patch operations for deterministic WF rules:
    - WF001: add missing states to states[]
    - WF002: patch initial state doc_status to 0 (if single initial state)
    - WF004: add missing role to app.roles and permission row on document_type
    - WF005 & WF011: add/repair workflow_state field with read_only: true and matching state options
    - WF007: set is_submittable: true if any state doc_status >= 1
    - WF009: drop duplicate transition

    Never invent new business states or arbitrary transitions for WF002/WF003.
    """
    if not spec.app:
        return SpecPatch(description="Empty repair patch", operations=[])

    original_dict = spec.model_dump(exclude_none=True)
    target_spec = AppSpecV2.model_validate(original_dict)
    app = target_spec.app
    if not app:
        return SpecPatch(description="Empty repair patch", operations=[])

    mutated = False

    for wf in app.workflows:
        existing_states = {s.state for s in wf.states}

        # WF001: Add missing states referenced in transitions
        for t in wf.transitions:
            for s_name in (t.state, t.next_state):
                if s_name and s_name not in existing_states:
                    wf.states.append(
                        WorkflowState(
                            state=s_name,
                            doc_status=0,
                            style="",
                            allow_edit="System Manager",
                        )
                    )
                    existing_states.add(s_name)
                    mutated = True

        # WF002: If single initial state has doc_status != 0, patch to 0
        incoming: dict[str, int] = {s.state: 0 for s in wf.states}
        for t in wf.transitions:
            if t.next_state in incoming:
                incoming[t.next_state] += 1
        initial = [s for s, count in incoming.items() if count == 0]
        if len(initial) == 1:
            init_s = next((s for s in wf.states if s.state == initial[0]), None)
            if init_s and init_s.doc_status != 0:
                init_s.doc_status = 0
                mutated = True

        # WF004: Role presence in app.roles and target DocType permissions
        dt = next((d for d in app.doctypes if d.name == wf.document_type), None)
        allow_edit_roles = {s.allow_edit for s in wf.states if s.allow_edit}
        state_doc_status = {s.state: s.doc_status for s in wf.states}
        submit_roles = {
            t.allowed
            for t in wf.transitions
            if state_doc_status.get(t.next_state, 0) == 1 and t.allowed
        }
        cancel_roles = {
            t.allowed
            for t in wf.transitions
            if state_doc_status.get(t.next_state, 0) == 2 and t.allowed
        }
        all_wf_roles = allow_edit_roles | {t.allowed for t in wf.transitions if t.allowed}

        roles_set = set(app.roles)
        for r in all_wf_roles:
            if r not in roles_set:
                app.roles.append(r)
                roles_set.add(r)
                mutated = True

        if dt:
            existing_perm_roles = {p.role: p for p in dt.permissions}
            for r in all_wf_roles:
                is_write = r in allow_edit_roles
                is_submit = r in submit_roles
                is_cancel = r in cancel_roles

                if r not in existing_perm_roles:
                    dt.permissions.append(
                        PermissionSpec(
                            role=r,
                            read=True,
                            write=is_write,
                            create=is_write,
                            submit=is_submit,
                            cancel=is_cancel,
                        )
                    )
                    mutated = True
                else:
                    perm = existing_perm_roles[r]
                    if (
                        not perm.read
                        or (is_write and not perm.write)
                        or (is_submit and not perm.submit)
                        or (is_cancel and not perm.cancel)
                    ):
                        perm.read = True
                        if is_write:
                            perm.write = True
                        if is_submit:
                            perm.submit = True
                        if is_cancel:
                            perm.cancel = True
                        mutated = True

            # WF005 & WF011: workflow_state field presence, read_only, and options
            state_names = [s.state for s in wf.states]
            newline_options = "\n".join(state_names)
            wf_field_name = wf.workflow_state_field or "workflow_state"
            wf_field = next((f for f in dt.fields if f.fieldname == wf_field_name), None)
            has_submittable = any(s.doc_status >= 1 for s in wf.states)

            if not wf_field:
                dt.fields.append(
                    FieldSpec(
                        fieldname=wf_field_name,
                        label="Workflow State",
                        fieldtype="Select",
                        options=newline_options,
                        read_only=True,
                        in_list_view=True,
                        in_standard_filter=True,
                        allow_on_submit=has_submittable,
                    )
                )
                mutated = True
            else:
                if (
                    wf_field.fieldtype != "Select"
                    or wf_field.options != newline_options
                    or not wf_field.read_only
                ):
                    wf_field.fieldtype = "Select"
                    wf_field.options = newline_options
                    wf_field.read_only = True
                    wf_field.in_list_view = True
                    wf_field.in_standard_filter = True
                    if has_submittable:
                        wf_field.allow_on_submit = True
                    mutated = True

            # WF007: Set is_submittable = True if any state doc_status >= 1
            if has_submittable and not dt.is_submittable:
                dt.is_submittable = True
                mutated = True

        # WF009: Drop duplicate transitions
        seen_t: set[tuple[str, str]] = set()
        unique_transitions: list[WorkflowTransition] = []
        for t in wf.transitions:
            key = (t.state.strip(), t.action.strip())
            if key not in seen_t:
                seen_t.add(key)
                unique_transitions.append(t)
            else:
                mutated = True
        wf.transitions = unique_transitions

    if not mutated:
        return SpecPatch(description="No structural workflow repairs needed", operations=[])

    target_dict = target_spec.model_dump(exclude_none=True)
    return make_spec_patch(original_dict, target_dict, description="Heal workflow validation errors")


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
        # 1. Deterministic workflow repair
        wf_patch = heal_workflow_errors(input_data.current_spec, input_data.validation_report)
        if wf_patch.operations:
            return wf_patch

        # 2. Check if remaining errors are non-structural WF002 / WF003
        detailed_rules = {e.rule_id for e in input_data.validation_report.detailed_errors if e.rule_id}
        if detailed_rules and detailed_rules.issubset({"WF002", "WF003"}):
            logger.info("Non-structural WF002/WF003 detected; escalating to Failed without hallucinating states.")
            return SpecPatch(description="Escalate to failed: cannot fix workflow graph structurally", operations=[])

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
