"""
planner.py — LLM brain for the AI Frappe App Builder.

Responsibilities:
  1. Maintain the system prompt that guides the LLM.
  2. Call OpenRouter (OpenAI-compatible) with the full conversation history.
  3. Parse the JSON response into an AppSpec.
  4. Persist the spec to the database.
  5. Provide site context introspection via FrappeClient.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import (
    Message,
    add_message,
    get_messages,
    save_app_spec,
    update_session_status,
)
from models import AppSpec
import decide

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Master system prompt — the AI planner's constitution
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the Planner for an AI Frappe app builder. Your only output is an App Spec: a JSON document. Downstream tools validate and apply it; you never create anything yourself.

## Your core rule: DO NOT HARDCODE OR ASSUME. ASK QUESTIONS ONE BY ONE.
1. The user requires an interactive interview. You MUST NOT hardcode or make silent assumptions about their business logic.
2. In each discovery turn, ask EXACTLY ONE focused question (one by one) to clarify their requirements.
3. Key areas to clarify one by one:
   - Core transaction lifecycle (what starts a booking/order, what approves it, what closes it)
   - Branches / multi-location setup
   - Money events (deposits, traffic fines, extra charges, settlement)
   - ERPNext integration (reuse existing Customer/Sales Invoice vs create custom standalone)
   - User roles and external portal users
   - Reports and key dashboard metrics
4. Provide 3-4 clear, helpful options for each question so the user can easily choose.

## Frappe rules you must follow when building the spec
**DocType naming**: Title Case, singular ("Rental Agreement", not "rental_agreements").
**Field names**: snake_case, lowercase, no spaces, no leading digits. Never use reserved names: name, owner, creation, modified, modified_by, docstatus, idx, parent, parentfield, parenttype, doctype, _user_tags, _comments, _assign, _liked_by.
**Field types and required options**:
- Link: options = target DocType name
- Table: options = child DocType (must have istable: true)
- Select: options = newline-separated values
- Currency fields: options = fieldname of currency field or Company:company:default_currency
**Naming (autoname)**: naming_series: with naming_series_options like RA-.YYYY.-.##### OR field:fieldname OR hash (for child tables)
**Flags**: istable: true for child tables. is_submittable: true only for immutable documents. track_changes: true on anything users edit after creation.
**Permissions**: one row per role. Always include System Manager with full rights.
**Workflows**: only when a document really moves through states with different actors.
**ERPNext conventions**: every transaction has company (Link Company). Money documents link to Customer.

## Output contract
Return ONLY valid JSON. No prose, no markdown fences.

When you need clarification from the client (ALWAYS ask questions one by one first):
{
  "status": "needs_input",
  "questions": [
    {
      "id": "q1",
      "question": "Your single, clear question here",
      "why_it_matters": "Why this affects the Frappe DocType/Workflow schema",
      "options": ["Option A", "Option B", "Option C"],
      "default": "Option A"
    }
  ],
  "assumptions": [],
  "app": null
}

When the client has answered the key discovery questions (or says 'build it' / 'proceed'):
{
  "status": "ready",
  "spec_version": "1.0",
  "questions": [],
  "assumptions": ["List of confirmed client requirements"],
  "app": {
    "app_name": "snake_case_name",
    "title": "Human Title",
    "mode": "app",
    "requires_erpnext": true,
    "modules": ["Module Name"],
    "roles": ["Role Name"],
    "doctypes": [...],
    "workflows": [...],
    "server_scripts": [...],
    "client_scripts": [...],
    "reports": [...],
    "dashboard": {...},
    "sample_data": {...}
  }
}"""

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


# ---------------------------------------------------------------------------
# Site context
# ---------------------------------------------------------------------------


async def get_site_context(frappe_client: Any) -> dict:
    """
    Pull site metadata so the planner can avoid re-creating existing
    DocTypes/Modules/Roles and understand what ERPNext features are available.
    """
    try:
        return await frappe_client.introspect_site()
    except Exception as exc:
        logger.warning("Could not introspect site: %s", exc)
        return {"installed_apps": [], "doctypes": [], "modules": [], "roles": []}


# ---------------------------------------------------------------------------
# Core planner
# ---------------------------------------------------------------------------


async def _call_llm(messages: list[dict], expect_json: bool = True) -> str:
    """
    Send messages to the configured LLM API (Ollama Cloud / OpenAI compatible)
    and return the raw text response.
    """
    base_url = settings.get_effective_base_url()
    api_key = settings.get_effective_llm_key()
    model = settings.get_effective_llm_model()

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,   # low temperature for deterministic output
        "max_tokens": 8192,
    }
    if expect_json:
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    logger.info("Calling LLM at %s with model %s", base_url, model)

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        if resp.status_code >= 400:
            logger.error("LLM error response: %s", resp.text)
        resp.raise_for_status()
        data = resp.json()

    try:
        content = data["choices"][0]["message"]["content"]
        # Handle reasoning models where output might be in thinking / reasoning_content
        if not content and "reasoning_content" in data["choices"][0]["message"]:
            content = data["choices"][0]["message"]["reasoning_content"]
        return content or ""
    except (KeyError, IndexError) as exc:
        raise ValueError(f"Unexpected LLM response shape: {data}") from exc


def _parse_text_as_questions(text: str) -> dict[str, Any]:
    """Fallback parser when model emits markdown questions instead of strict JSON."""
    import re

    q_matches = re.findall(r"\*\*\d+\.\s*(.*?)\*\*", text)
    if not q_matches:
        q_matches = [line.strip("* -# ") for line in text.splitlines() if "?" in line]

    why_match = re.search(r"\*Why this matters:\*\s*(.*?)(?=\n\s*\*|\n\n|$)", text, re.DOTALL)
    options_match = re.search(r"\*Options:\*\s*(.*?)(?=\n\s*\*|\n\n|$)", text, re.DOTALL)

    why_text = why_match.group(1).strip() if why_match else "Clarifying requirements for schema design"
    options_list = [opt.strip() for opt in options_match.group(1).split(",")] if options_match else []

    q_text = q_matches[0] if q_matches else text.strip().splitlines()[0]
    return {
        "status": "needs_input",
        "questions": [
            {
                "id": "q1",
                "question": q_text,
                "why_it_matters": why_text,
                "options": options_list,
            }
        ],
        "assumptions": [],
        "app": None,
    }


def _parse_app_spec(raw: str) -> AppSpec:
    """
    Parse the LLM's raw text output into an AppSpec.
    Ultra-resilient: handles markdown fences, embedded JSON substring, or plain text fallback.
    """
    import re

    text = raw.strip()

    # 1. Strip markdown fences if present
    if "```" in text:
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fence_match:
            text = fence_match.group(1).strip()

    # 2. Extract JSON between first { and last }
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_candidate = text[start_idx : end_idx + 1]
        try:
            data = json.loads(json_candidate)
            if "status" not in data:
                data["status"] = "ready" if data.get("app") else "needs_input"
            if "questions" not in data and "question" in data:
                q_obj = data["question"]
                if isinstance(q_obj, str):
                    data["questions"] = [{"id": "q1", "question": q_obj}]
                elif isinstance(q_obj, dict):
                    data["questions"] = [q_obj]
            return AppSpec(**data)
        except Exception as e:
            logger.debug("Failed parsing JSON candidate substring: %s", e)

    # 3. Fallback: Parse markdown questions if model answered in natural language
    try:
        data = _parse_text_as_questions(raw)
        return AppSpec(**data)
    except Exception as e:
        logger.error("Could not parse as questions fallback: %s", e)

    # 4. Final safety net: Never crash with Expecting value
    clean_line = raw.strip().splitlines()[0] if raw.strip() else "Could you clarify what kind of records you need?"
    return AppSpec(
        status="needs_input",
        questions=[{
            "id": "q1",
            "question": clean_line[:300],
            "why_it_matters": "Determines Frappe schema",
            "options": [],
        }],
        assumptions=[],
        app=None,
    )


def _format_questions_as_text(questions: list[dict]) -> str:
    """Render the questions list as a human-readable assistant message."""
    if not questions:
        return "I need a bit more information before I can build your spec."

    lines = ["I have a few questions before I can generate your app:\n"]
    for i, q in enumerate(questions, 1):
        lines.append(f"**{i}. {q.get('question', '')}**")
        why = q.get("why_it_matters", "")
        if why:
            lines.append(f"   *Why this matters:* {why}")
        options = q.get("options", [])
        if options:
            lines.append(f"   *Options:* {', '.join(options)}")
        default = q.get("default", "")
        if default:
            lines.append(f"   *Default if not specified:* {default}")
        lines.append("")

    return "\n".join(lines)


async def plan(
    session_id: str,
    db: AsyncSession,
    site_context: dict | None = None,
) -> AppSpec:
    """
    Run one planning turn:
      1. Load full message history from DB.
      2. Call OpenRouter with system prompt + history.
      3. Parse response into AppSpec.
      4. Persist spec (and assistant message) to DB.
      5. Return AppSpec.

    Parameters
    ----------
    session_id    The session UUID.
    db            Async SQLAlchemy session.
    site_context  Optional dict from get_site_context(); empty dict if not provided.
    """
    if site_context is None:
        site_context = {}

    # --- Build LLM message list ---
    db_messages: list[Message] = await get_messages(db, session_id)

    llm_messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Decision layer: Jev identifies business archetype
    first_user_text = next((m.content for m in db_messages if m.role == "user"), "")
    if first_user_text:
        try:
            archetype = await decide.choose_archetype(first_user_text)
            llm_messages.append({
                "role": "system",
                "content": f"Jev Decision Layer: Business archetype identified as '{archetype}'. Optimize schema accordingly.",
            })
        except Exception as j_exc:
            logger.debug("Jev archetype call skipped: %s", j_exc)

    # Inject site context as a system note if available
    if site_context and (site_context.get("doctypes") or site_context.get("installed_apps")):
        ctx_summary = (
            f"Site context: "
            f"installed_apps={site_context.get('installed_apps', [])}, "
            f"modules={site_context.get('modules', [])}, "
            f"existing_roles={site_context.get('roles', [])}, "
            f"total_doctypes={len(site_context.get('doctypes', []))}."
        )
        llm_messages.append({"role": "system", "content": ctx_summary})

    for msg in db_messages:
        if msg.role in ("user", "assistant"):
            llm_messages.append({"role": msg.role, "content": msg.content})

    # --- Call LLM ---
    logger.info("Calling configured LLM for session %s (%d messages)", session_id, len(llm_messages))
    raw_response = await _call_llm(llm_messages)
    logger.debug("LLM raw response: %s", raw_response[:300])

    # --- Parse ---
    spec = _parse_app_spec(raw_response)

    # --- Determine assistant reply text ---
    if spec.status == "needs_input":
        assistant_text = _format_questions_as_text(spec.questions)
    else:
        assumptions = spec.assumptions
        assistant_text = (
            "✅ I have enough information to build your app spec!\n\n"
            + (
                "**Assumptions made:**\n"
                + "\n".join(f"- {a}" for a in assumptions)
                if assumptions
                else ""
            )
        )

    # --- Persist assistant message ---
    await add_message(db, session_id, "assistant", assistant_text)

    # --- Persist spec ---
    spec_json = json.dumps(spec.model_dump(), ensure_ascii=False)
    await save_app_spec(db, session_id, spec_json)

    # --- Update session status ---
    new_status = "planned" if spec.status == "ready" else "discovery"
    await update_session_status(db, session_id, new_status)

    return spec


async def auto_heal_spec(
    session_id: str,
    db: AsyncSession,
    spec: AppSpec,
    errors: list[str],
    site_context: dict,
    max_retries: int = 3,
) -> tuple[AppSpec, bool, list[str]]:
    """
    Subagent Healing Loop:
    When validator catches errors, this repair agent automatically fixes
    the AppSpec using the exact error traces without human intervention.
    """
    current_spec = spec
    current_errors = errors
    all_msgs: list[str] = []

    for attempt in range(1, max_retries + 1):
        logger.info(
            "Auto-healing attempt %d/%d for session %s with %d errors",
            attempt, max_retries, session_id, len(current_errors),
        )

        error_bullets = "\n".join(f"- {e}" for e in current_errors)
        heal_prompt = f"""You are the Frappe App Spec Repair Subagent.
The previous Frappe App Spec you generated failed validation with the following {len(current_errors)} errors:

{error_bullets}

Here is the invalid spec JSON:
{json.dumps(current_spec.model_dump(), indent=2)}

FIX ALL of the errors above according to Frappe rules:
1. Ensure all Link fields point to known DocTypes or core ERPNext/Frappe DocTypes (Customer, Company, Supplier, Item, User, etc.) or create the missing DocType in the spec.
2. Ensure every DocType has a Title Case name, module, and autoname.
3. Ensure all workflows have document_type, reachable states, and valid transitions.
4. Return ONLY the corrected JSON App Spec with status="ready". No markdown fences, no explanation."""

        try:
            raw_fixed = await _call_llm([{"role": "system", "content": heal_prompt}])
            fixed_spec = _parse_app_spec(raw_fixed)
            from validator import validate_with_jev
            is_valid, validation_msgs, _ = await validate_with_jev(fixed_spec, site_context)
            new_errors = [m for m in validation_msgs if m.startswith("ERROR:")]

            if is_valid or not new_errors:
                logger.info("Auto-healing SUCCEEDED on attempt %d!", attempt)
                spec_json = json.dumps(fixed_spec.model_dump(), ensure_ascii=False)
                await save_app_spec(db, session_id, spec_json)
                return fixed_spec, True, validation_msgs
            else:
                current_spec = fixed_spec
                current_errors = new_errors
                all_msgs = validation_msgs
        except Exception as exc:
            logger.warning("Healing attempt %d encountered exception: %s", attempt, exc)

    return current_spec, False, all_msgs or current_errors
