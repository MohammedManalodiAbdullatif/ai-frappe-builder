"""
routers/chat.py — Multi-turn discovery conversation endpoints.

POST /chat/start   — Begin a new session with an initial message.
POST /chat/message — Continue an existing session with a follow-up message.

When the planner returns "ready", the spec is automatically validated and
applied to Frappe with NO human approval gate.
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
    add_message,
    create_session,
    get_db,
    get_session,
    get_current_spec,
    update_session_status,
    save_app_spec,
)
from frappe_client import FrappeClient
from models import AppSpec, ChatMessageRequest, ChatResponse, ChatStartRequest

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_frappe_client(session) -> FrappeClient:
    """Build a FrappeClient from session-stored credentials."""
    return FrappeClient(
        base_url=session.frappe_url or "",
        api_key=session.frappe_api_key or "",
        api_secret=session.frappe_api_secret or "",
    )


async def _auto_validate_and_apply(
    spec: AppSpec,
    session_id: str,
    db: AsyncSession,
    frappe_client: FrappeClient,
) -> dict:
    """
    Fully automatic pipeline once spec is ready:
      validate → apply → return summary.
    No human intervention required.
    """
    # --- Validate ---
    try:
        async with frappe_client as fc:
            site_ctx = await planner.get_site_context(fc)
    except Exception as exc:
        logger.warning("Could not get site context for validation: %s", exc)
        site_ctx = {"doctypes": [], "modules": [], "roles": [], "installed_apps": []}

    is_valid, validation_msgs, readiness_score = await validator.validate_with_jev(spec, site_ctx)

    errors_only = [m for m in validation_msgs if m.startswith("ERROR:")]
    warnings_only = [m for m in validation_msgs if m.startswith("WARNING:")]

    # Save validation result back to spec record
    db_spec = await get_current_spec(db, session_id)
    if db_spec:
        db_spec.validation_result = json.dumps(
            {
                "valid": is_valid,
                "readiness_score": readiness_score,
                "errors": errors_only,
                "warnings": warnings_only,
            }
        )
        await db.commit()

    if not is_valid:
        logger.info("Validation errors found for session %s. Triggering Repair Subagent...", session_id)
        spec, is_valid, heal_msgs = await planner.auto_heal_spec(
            session_id, db, spec, errors_only, site_ctx
        )
        errors_only = [m for m in heal_msgs if m.startswith("ERROR:")]
        warnings_only = [m for m in heal_msgs if m.startswith("WARNING:")]

    if not is_valid:
        await update_session_status(db, session_id, "failed")
        return {
            "apply_status": "validation_failed",
            "validation_errors": errors_only,
            "created": [],
            "errors": errors_only,
            "preview_urls": [],
        }

    # --- Apply or Export ---
    await update_session_status(db, session_id, "applying")
    created: list[str] = []
    errors: list[str] = []
    preview_urls: list[str] = []

    # If Frappe site credentials are provided, apply directly to the site
    if frappe_client.base_url and getattr(frappe_client, "_headers", {}).get("Authorization") != "token :":
        try:
            async with frappe_client as fc:
                result = await applier.apply_spec(session_id, spec, fc)
                created = result.get("created", [])
                errors = result.get("errors", [])
                preview_urls = result.get("preview_urls", [])
        except Exception as exc:
            logger.warning("Remote Frappe apply skipped: %s", exc)

    # Always export the complete installable Frappe app to disk and .zip archive
    try:
        from exporter import export_app
        exp_res = await export_app(spec, "/tmp/frappe_exports")
        for f in exp_res.get("files_created", []):
            created.append(f"Exported: {f.split('/')[-1]}")
        logger.info("Successfully exported Frappe app to %s", exp_res.get("app_path"))
    except Exception as exp_err:
        errors.append(f"Export error: {exp_err}")

    final_status = "done" if created else ("partial" if errors else "failed")
    await update_session_status(db, session_id, final_status)

    return {
        "apply_status": final_status,
        "validation_warnings": warnings_only,
        "created": created,
        "errors": errors,
        "preview_urls": preview_urls,
    }


# ---------------------------------------------------------------------------
# POST /chat/start
# ---------------------------------------------------------------------------


@router.post("/start", response_model=ChatResponse)
async def chat_start(
    body: ChatStartRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Start a new planning session.

    Creates a session in the DB, stores the client's first message,
    calls the planner, and — if the spec is immediately ready —
    automatically validates and applies it.
    """
    # Create session
    sess = await create_session(
        db,
        client_name=body.client_name,
        frappe_url=body.frappe_url,
        frappe_api_key=body.frappe_api_key,
        frappe_api_secret=body.frappe_api_secret,
    )

    # Store user message
    await add_message(db, sess.id, "user", body.message)

    # Get site context
    fc = _make_frappe_client(sess)
    try:
        async with fc as client:
            site_ctx = await planner.get_site_context(client)
    except Exception as exc:
        logger.warning("Site context unavailable: %s", exc)
        site_ctx = {}

    # Plan
    try:
        spec = await planner.plan(sess.id, db, site_ctx)
    except Exception as exc:
        logger.error("Planner error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Planner error: {exc}")

    apply_result: dict | None = None
    if spec.status == "ready":
        apply_result = await _auto_validate_and_apply(
            spec, sess.id, db, _make_frappe_client(sess)
        )

    return ChatResponse(
        session_id=sess.id,
        response=_build_response_text(spec, apply_result),
        status=spec.status,
        questions=spec.questions,
        assumptions=spec.assumptions,
        spec=spec.app if spec.status == "ready" else None,
    )


# ---------------------------------------------------------------------------
# POST /chat/message
# ---------------------------------------------------------------------------


@router.post("/message", response_model=ChatResponse)
async def chat_message(
    body: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Continue an existing planning session.

    Appends the user's message, re-runs the planner with full history,
    and automatically applies the spec if it reaches "ready" status.
    """
    sess = await get_session(db, body.session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")

    if sess.status in ("done", "applying"):
        raise HTTPException(
            status_code=400,
            detail=f"Session is already in '{sess.status}' state.",
        )

    # Store user message
    await add_message(db, sess.id, "user", body.message)

    # Get site context
    fc = _make_frappe_client(sess)
    try:
        async with fc as client:
            site_ctx = await planner.get_site_context(client)
    except Exception as exc:
        logger.warning("Site context unavailable: %s", exc)
        site_ctx = {}

    # Plan
    try:
        spec = await planner.plan(sess.id, db, site_ctx)
    except Exception as exc:
        logger.error("Planner error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Planner error: {exc}")

    apply_result: dict | None = None
    if spec.status == "ready":
        apply_result = await _auto_validate_and_apply(
            spec, sess.id, db, _make_frappe_client(sess)
        )

    return ChatResponse(
        session_id=sess.id,
        response=_build_response_text(spec, apply_result),
        status=spec.status,
        questions=spec.questions,
        assumptions=spec.assumptions,
        spec=spec.app if spec.status == "ready" else None,
    )


# ---------------------------------------------------------------------------
# Response text builder
# ---------------------------------------------------------------------------


def _build_response_text(spec: AppSpec, apply_result: dict | None) -> str:
    if spec.status == "needs_input":
        from planner import _format_questions_as_text
        return _format_questions_as_text(spec.questions)

    lines = ["✅ **App spec is ready!** Building your app on Frappe now...\n"]

    if apply_result:
        status = apply_result.get("apply_status", "unknown")
        created = apply_result.get("created", [])
        errors = apply_result.get("errors", [])
        urls = apply_result.get("preview_urls", [])
        warnings = apply_result.get("validation_warnings", [])

        if status == "validation_failed":
            lines.append("❌ **Validation failed** — spec has errors:\n")
            for e in errors:
                lines.append(f"  - {e}")
        elif status in ("done", "partial"):
            lines.append(f"🎉 **Build {status}!**\n")
            if created:
                lines.append("**Created:**")
                for c in created:
                    lines.append(f"  - {c}")
            if warnings:
                lines.append("\n**Warnings:**")
                for w in warnings:
                    lines.append(f"  - {w}")
            if errors:
                lines.append("\n**Errors:**")
                for e in errors:
                    lines.append(f"  - {e}")
            if urls:
                lines.append("\n**Preview URLs:**")
                for u in urls:
                    lines.append(f"  - {u}")
        else:
            lines.append("❌ **Apply failed.**\n")
            for e in errors:
                lines.append(f"  - {e}")

    return "\n".join(lines)
