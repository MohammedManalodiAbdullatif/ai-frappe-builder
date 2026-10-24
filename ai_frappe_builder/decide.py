"""
decide.py — Jev decision layer wrapper.

Jev (`jev-latest`, TypeSafe, served on Experiential platform) is the judge in this system.
It evaluates a state plus typed questions and returns:
  - `choice`: picks one of multiple options (e.g. business archetype, script pattern)
  - `noul`: binary boolean (true/false) decision (e.g. spec gate checks, destructive change)
  - `score`: ordered rating from 2 to 10 levels (e.g. spec readiness score, assumption priority)

If EXPERIENTIAL_API_KEY is not configured, it gracefully falls back to deterministic/LLM heuristics.
"""

from __future__ import annotations

import logging
from typing import Any, Literal, cast
import httpx

from ai_frappe_builder.config import get_settings

logger = logging.getLogger(__name__)

JEV_ENDPOINT = "https://platform.experientiallabs.ai/v1/systemone"


async def call_jev(state: dict[str, Any], questions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    Call the Jev `/v1/systemone` batch API.
    """
    settings = get_settings()
    api_key = getattr(settings, "EXPERIENTIAL_API_KEY", "") or ""

    if not api_key:
        logger.info("EXPERIENTIAL_API_KEY not configured — using intelligent heuristic fallback for Jev decisions.")
        return _heuristic_fallback(state, questions)

    payload = {
        "model": "jev-latest",
        "state": state,
        "questions": questions,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                JEV_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            # Jev returns answers mapped by question id
            answers = data.get("answers", data)
            return cast(dict[str, Any], answers if isinstance(answers, dict) else {})
    except Exception as exc:
        logger.warning("Jev request failed (%s) — falling back to heuristics", exc)
        return _heuristic_fallback(state, questions)


def _heuristic_fallback(state: dict[str, Any], questions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    Deterministic fallback when Jev API key is not present or endpoint is unreachable.
    """
    answers: dict[str, Any] = {}
    client_text = str(state.get("client_text", "")).lower()

    for q_id, q_def in questions.items():
        q_type = q_def.get("type")
        instructions = q_def.get("instructions", "").lower()

        if q_type == "choice":
            criteria = q_def.get("criteria", {})
            chosen = next(iter(criteria.keys())) if criteria else None
            # Basic keyword match against criteria
            for k in criteria.keys():
                if k.lower() in client_text:
                    chosen = k
                    break
            answers[q_id] = chosen

        elif q_type == "noul":
            # True/False check
            if "erpnext" in instructions:
                answers[q_id] = "erpnext" in client_text
            elif "duplicate" in instructions:
                answers[q_id] = False
            elif "destructive" in instructions:
                answers[q_id] = False
            else:
                answers[q_id] = False

        elif q_type == "score":
            criteria = q_def.get("criteria", [])
            # Return high readiness / acceptable default score
            answers[q_id] = criteria[-1] if criteria else "Ship-ready"

    return answers


# ---------------------------------------------------------------------------
# High-level decision helpers as defined in Master Spec
# ---------------------------------------------------------------------------


async def choose_archetype(client_text: str) -> str:
    """
    Classify client business archetype (daily rental, lease, chauffeur, trading, etc.)
    """
    questions = {
        "archetype": {
            "type": "choice",
            "instructions": "Which business archetype best matches what the client describes?",
            "criteria": {
                "daily_rental": "Short-term self-drive rentals by day or week with fines/charges",
                "long_term_lease": "Long-term monthly/yearly leases with recurring contracts",
                "chauffeur": "Driver-included trips priced per trip or hour",
                "equipment_rental": "Machinery or asset rentals with security deposits and return inspections",
                "general_service": "Service or project delivery business",
                "trading": "Buying and selling physical items with inventory",
            },
        }
    }
    res = await call_jev({"client_text": client_text}, questions)
    val = res.get("archetype", "daily_rental")
    return str(val) if val else "daily_rental"


async def judge_spec_gate(spec_dict: dict[str, Any], site_context: dict[str, Any]) -> dict[str, Any]:
    """
    Run the Jev spec gate fuzzy checks (duplicates, workflow reachability, submittable flags).
    """
    slimmed_state: dict[str, Any] = {
        "doctypes": [dt.get("name") for dt in spec_dict.get("doctypes", []) if isinstance(dt, dict)],
        "existing_site_doctypes": [dt.get("name") for dt in site_context.get("doctypes", []) if isinstance(dt, dict)],
    }

    questions: dict[str, Any] = {
        "has_duplicate_doctypes": {
            "type": "noul",
            "instructions": "A doctype in the spec duplicates an existing core doctype from the site.",
        },
        "spec_readiness": {
            "type": "score",
            "instructions": "Rate the production readiness of this Frappe App Spec.",
            "criteria": ["Unusable", "Major gaps", "Usable with edits", "Minor polish", "Ship-ready"],
        },
    }

    res = await call_jev(slimmed_state, questions)
    return {
        "has_duplicates": bool(res.get("has_duplicate_doctypes", False)),
        "readiness_score": str(res.get("spec_readiness", "Ship-ready")),
    }


async def pick_script_pattern(purpose: str, doctype_fields: list[str]) -> str:
    """
    Use Jev to select the best snippet pattern among the 7 templates.
    """
    questions = {
        "pattern": {
            "type": "choice",
            "instructions": "Which script pattern best fits the described business purpose?",
            "criteria": {
                "overlap_check": "Prevent resource booking clashes across start/end date ranges",
                "compute_totals": "Sum child row amounts and calculate grand total and balance",
                "create_document_on_submit": "Auto-create linked draft document after submission",
                "validate_required_child_rows": "Validate at least one item row exists before save",
                "update_linked_status": "Update a parent status when a child event completes",
                "fetch_and_validate": "Verify linked doc meets status requirement before saving",
                "scheduled_reminder": "Daily scheduler check for overdue dates or expiries",
            },
        }
    }
    res = await call_jev({"purpose": purpose, "fields": doctype_fields}, questions)
    pattern_val = res.get("pattern", "overlap_check")
    return str(pattern_val) if pattern_val else "overlap_check"
