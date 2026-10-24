"""
routers/apply.py — Manually trigger apply for a session that already has a spec.

POST /apply/{session_id}
  Validates the current spec and applies it to Frappe — no approval needed.
  This endpoint is useful if the automatic apply after /chat/message failed
  and you want to retry.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import applier
import planner
import validator
from database import (
    get_current_spec,
    get_db,
    get_session,
    update_session_status,
)
from frappe_client import FrappeClient
from models import AppSpec, ApplyResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{session_id}", response_model=ApplyResponse)
async def apply_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApplyResponse:
    """
    Apply the current App Spec to Frappe.

    This runs automatically after /chat/message when the spec is ready.
    Call this endpoint manually to retry a failed apply.
    """
    sess = await get_session(db, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")

    db_spec = await get_current_spec(db, session_id)
    if not db_spec:
        raise HTTPException(
            status_code=404,
            detail="No spec found for this session. Complete the chat first.",
        )

    # Parse spec
    try:
        spec_dict = json.loads(db_spec.spec_json)
        spec = AppSpec(**spec_dict)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Spec parse error: {exc}")

    if spec.status != "ready":
        raise HTTPException(
            status_code=400,
            detail="Spec is not in 'ready' state. Continue the conversation.",
        )

    # --- Validate ---
    fc = FrappeClient(
        base_url=sess.frappe_url or "",
        api_key=sess.frappe_api_key or "",
        api_secret=sess.frappe_api_secret or "",
    )
    try:
        async with fc as client:
            site_ctx = await planner.get_site_context(client)
    except Exception as exc:
        logger.warning("Could not get site context: %s", exc)
        site_ctx = {"doctypes": [], "modules": [], "roles": [], "installed_apps": []}

    is_valid, msgs = validator.validate(spec, site_ctx)
    errors_only = [m for m in msgs if m.startswith("ERROR:")]

    if not is_valid:
        await update_session_status(db, session_id, "failed")
        return ApplyResponse(
            status="validation_failed",
            created=[],
            errors=errors_only,
            preview_urls=[],
        )

    # --- Apply ---
    await update_session_status(db, session_id, "applying")
    try:
        async with fc as client:
            result = await applier.apply_spec(session_id, spec, client)
    except Exception as exc:
        await update_session_status(db, session_id, "failed")
        raise HTTPException(status_code=500, detail=str(exc))

    final_status = "done" if result["status"] in ("done", "partial") else "failed"
    await update_session_status(db, session_id, final_status)

    return ApplyResponse(
        status=result["status"],
        created=result["created"],
        errors=result["errors"],
        preview_urls=result["preview_urls"],
    )
