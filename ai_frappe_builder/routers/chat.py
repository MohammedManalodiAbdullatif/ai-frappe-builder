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
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
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
    frappe_url = body.frappe_url or "http://crm.localhost:8015"
    frappe_api_key = body.frappe_api_key or "992f21dbfdb7f47"
    frappe_api_secret = body.frappe_api_secret or "acf9538d97bf2a6"

    # Create session
    sess = await create_session(
        db,
        client_name=body.client_name,
        frappe_url=frappe_url,
        frappe_api_key=frappe_api_key,
        frappe_api_secret=frappe_api_secret,
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

    # Run through Orchestrator state machine
    try:
        from ai_frappe_builder.agents.orchestrator import (
            get_orchestrator,
            get_or_create_orchestrator_session,
        )

        orch = get_orchestrator()
        orch_session = get_or_create_orchestrator_session(sess.id)
        orch_res = await orch.handle_user_message(orch_session, body.message, site_ctx)
    except Exception as exc:
        logger.error("Orchestrator error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Planner error: {exc}")

    # Persist assistant reply
    assistant_reply = orch_res.get("response", "")
    if orch_res.get("question") and orch_res["question"].get("text"):
        q_text = orch_res["question"]["text"]
        if q_text not in assistant_reply:
            assistant_reply = f"{assistant_reply}\n\n{q_text}".strip()
    await add_message(db, sess.id, "assistant", assistant_reply)

    if orch_res.get("spec"):
        try:
            await save_app_spec(db, sess.id, orch_res["spec"])
        except Exception as e:
            await db.rollback()
            logger.warning("Could not persist spec to DB: %s", e)

    return ChatResponse(
        session_id=sess.id,
        response=assistant_reply,
        status=orch_res.get("status", "needs_input"),
        questions=[orch_res["question"]] if orch_res.get("question") else [],
        assumptions=orch_res.get("assumptions", []),
        spec=orch_res.get("spec"),
        interview_turn=orch_res.get("interview_turn"),
        coverage=orch_res.get("coverage"),
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

    Appends the user's message, advances the Orchestrator discovery script or
    mutation pipeline, and updates state.
    """
    sess = await get_session(db, body.session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")

    if sess.status == "applying":
        raise HTTPException(
            status_code=400,
            detail="Session is currently applying changes to Frappe bench.",
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

    # Run through Orchestrator
    try:
        from ai_frappe_builder.agents.orchestrator import (
            get_orchestrator,
            get_or_create_orchestrator_session,
            hydrate_orchestrator_session,
        )

        orch = get_orchestrator()
        orch_session = get_or_create_orchestrator_session(sess.id)
        await hydrate_orchestrator_session(orch_session, db)
        orch_res = await orch.handle_user_message(orch_session, body.message, site_ctx)
    except Exception as exc:
        logger.error("Orchestrator error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Planner error: {exc}")

    # Persist assistant reply
    assistant_reply = orch_res.get("response", "")
    if orch_res.get("question") and orch_res["question"].get("text"):
        q_text = orch_res["question"]["text"]
        if q_text not in assistant_reply:
            assistant_reply = f"{assistant_reply}\n\n{q_text}".strip()
    await add_message(db, sess.id, "assistant", assistant_reply)

    if orch_res.get("spec"):
        try:
            await save_app_spec(db, sess.id, orch_res["spec"])
        except Exception as e:
            await db.rollback()
            logger.warning("Could not persist spec to DB: %s", e)

    return ChatResponse(
        session_id=sess.id,
        response=assistant_reply,
        status=orch_res.get("status", "needs_input"),
        questions=[orch_res["question"]] if orch_res.get("question") else [],
        assumptions=orch_res.get("assumptions", []),
        spec=orch_res.get("spec"),
        interview_turn=orch_res.get("interview_turn"),
        coverage=orch_res.get("coverage"),
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


class TestConnectionRequest(BaseModel):
    frappe_url: str
    frappe_api_key: str
    frappe_api_secret: str


@router.post("/test-connection")
async def test_frappe_connection(req: TestConnectionRequest) -> dict[str, Any]:
    """Test connectivity and introspect a running Frappe bench site."""
    fc = FrappeClient(
        base_url=req.frappe_url,
        api_key=req.frappe_api_key,
        api_secret=req.frappe_api_secret,
    )
    try:
        async with fc as client:
            site_ctx = await planner.get_site_context(client)
            return {
                "ok": True,
                "installed_apps": site_ctx.get("installed_apps", []),
                "doctypes_count": len(site_ctx.get("doctypes", [])),
                "modules_count": len(site_ctx.get("modules", [])),
                "roles_count": len(site_ctx.get("roles", [])),
            }
    except Exception as exc:
        logger.warning("Test connection failed: %s", exc)
        return {"ok": False, "error": str(exc)}

