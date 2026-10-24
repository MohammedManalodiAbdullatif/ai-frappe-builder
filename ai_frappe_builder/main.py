"""
main.py — FastAPI application entrypoint for the AI Frappe App Builder.

Endpoints:
  GET  /health               — Health check
  POST /chat/start           — Begin a new planning session
  POST /chat/message         — Continue a planning session
  GET  /plan/{session_id}    — Retrieve the current App Spec
  POST /apply/{session_id}   — Re-trigger apply (retry failed builds)
  POST /build                — One-shot endpoint: describe → build → preview URLs
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import init_db, get_db, create_session, add_message, get_messages, get_current_spec
from database import get_session as db_get_session
from routers import apply, chat, events, export, plan
import planner
import validator
import applier
from frappe_client import FrappeClient
from models import AppSpec
from sqlalchemy import select
from database import Session as DBSession, Message as DBMessage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: initialise DB on startup
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Frappe App Builder — initialising database…")
    await init_db()
    logger.info("Database ready.")
    yield
    logger.info("Shutting down.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Frappe App Builder",
    description=(
        "Describe your business in plain language. "
        "The AI asks questions, generates a Frappe App Spec, "
        "and automatically creates DocTypes/Workflows on your Frappe site."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Allow all origins for local development — tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers (Legacy and versioned /api/v1)
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(plan.router, prefix="/plan", tags=["Plan"])
app.include_router(apply.router, prefix="/apply", tags=["Apply"])
app.include_router(export.router, prefix="/export", tags=["Export"])

app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat v1"])
app.include_router(plan.router, prefix="/api/v1/plan", tags=["Plan v1"])
app.include_router(apply.router, prefix="/api/v1/apply", tags=["Apply v1"])
app.include_router(export.router, prefix="/api/v1/export", tags=["Export v1"])
app.include_router(events.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Meta"])
async def health():
    return {"status": "ok", "service": "AI Frappe App Builder"}


# ---------------------------------------------------------------------------
# GET /sessions — List all sessions
# GET /sessions/{session_id} — Full detail for one session
# ---------------------------------------------------------------------------


@app.get("/sessions", tags=["Sessions"])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """List all build sessions ordered by creation time (newest first)."""
    result = await db.execute(
        select(DBSession).order_by(DBSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [
        {
            "session_id": s.id,
            "client_name": s.client_name,
            "status": s.status,
            "frappe_url": s.frappe_url,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in sessions
    ]


@app.get("/sessions/{session_id}", tags=["Sessions"])
async def get_session_detail(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get full detail for one session including messages and current spec."""
    sess = await db_get_session(db, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await get_messages(db, session_id)
    spec_row = await get_current_spec(db, session_id)

    spec_data = None
    if spec_row:
        spec_data = {
            "version": spec_row.version,
            "is_current": spec_row.is_current,
            "created_at": spec_row.created_at.isoformat() if spec_row.created_at else None,
            "spec_json": json.loads(spec_row.spec_json) if spec_row.spec_json else None,
            "validation_result": (
                json.loads(spec_row.validation_result) if spec_row.validation_result else None
            ),
        }

    return {
        "session_id": sess.id,
        "client_name": sess.client_name,
        "status": sess.status,
        "frappe_url": sess.frappe_url,
        "created_at": sess.created_at.isoformat() if sess.created_at else None,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
        "current_spec": spec_data,
    }


# ---------------------------------------------------------------------------
# POST /build — One-shot fully-automatic endpoint
# ---------------------------------------------------------------------------


class BuildRequest(BaseModel):
    client_name: str
    description: str           # Plain-language business description
    frappe_url: str
    frappe_api_key: str
    frappe_api_secret: str
    # Optional follow-up answers to include in first turn
    extra_context: str = ""


class BuildResponse(BaseModel):
    session_id: str
    status: str                # "done" | "partial" | "needs_input" | "failed"
    created: list[str] = []
    errors: list[str] = []
    preview_urls: list[str] = []
    questions: list[dict] = []   # populated when AI needs more info
    assumptions: list[str] = []
    spec: dict | None = None


@app.post("/build", tags=["Build"], response_model=BuildResponse)
async def build(
    body: BuildRequest,
    db: AsyncSession = Depends(get_db),
) -> BuildResponse:
    """
    **One-shot build endpoint.**

    1. Creates a session.
    2. Sends the description to the AI planner.
    3. If the planner has enough info → validates → applies automatically.
    4. If the planner needs more info → returns questions (call /chat/message to answer).

    The entire flow runs with NO human approval gates.
    """
    # Compose initial user message
    user_msg = body.description
    if body.extra_context:
        user_msg += f"\n\nAdditional context: {body.extra_context}"

    # Create session
    sess = await create_session(
        db,
        client_name=body.client_name,
        frappe_url=body.frappe_url,
        frappe_api_key=body.frappe_api_key,
        frappe_api_secret=body.frappe_api_secret,
    )
    await add_message(db, sess.id, "user", user_msg)

    # Site context
    fc = FrappeClient(body.frappe_url, body.frappe_api_key, body.frappe_api_secret)
    try:
        async with fc as client:
            site_ctx = await planner.get_site_context(client)
    except Exception as exc:
        logger.warning("Could not get site context: %s", exc)
        site_ctx = {}

    # Plan
    try:
        spec: AppSpec = await planner.plan(sess.id, db, site_ctx)
    except Exception as exc:
        logger.error("Planner failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Planner error: {exc}")

    # If needs more info, return the questions
    if spec.status == "needs_input":
        return BuildResponse(
            session_id=sess.id,
            status="needs_input",
            questions=spec.questions,
            assumptions=spec.assumptions,
        )

    # Validate (Python hard rules + Jev decision gate)
    is_valid, msgs, readiness_score = await validator.validate_with_jev(spec, site_ctx)
    errors_only = [m for m in msgs if m.startswith("ERROR:")]
    warnings_only = [m for m in msgs if m.startswith("WARNING:")]
    logger.info("Jev readiness score for session %s: %s", sess.id, readiness_score)

    if not is_valid:
        logger.info("Validation errors found for session %s. Triggering Repair Subagent...", sess.id)
        spec, is_valid, heal_msgs = await planner.auto_heal_spec(
            sess.id, db, spec, errors_only, site_ctx
        )
        errors_only = [m for m in heal_msgs if m.startswith("ERROR:")]
        warnings_only = [m for m in heal_msgs if m.startswith("WARNING:")]

    if not is_valid:
        from database import update_session_status
        await update_session_status(db, sess.id, "failed")
        return BuildResponse(
            session_id=sess.id,
            status="validation_failed",
            errors=errors_only,
            assumptions=spec.assumptions,
            spec=spec.app,
        )

    # Apply
    from database import update_session_status
    await update_session_status(db, sess.id, "applying")

    try:
        async with fc as client:
            result = await applier.apply_spec(sess.id, spec, client)
    except Exception as exc:
        await update_session_status(db, sess.id, "failed")
        raise HTTPException(status_code=500, detail=str(exc))

    final_status = "done" if result["status"] in ("done", "partial") else "failed"
    await update_session_status(db, sess.id, final_status)

    return BuildResponse(
        session_id=sess.id,
        status=result["status"],
        created=result["created"],
        errors=result["errors"] + warnings_only,
        preview_urls=result["preview_urls"],
        assumptions=spec.assumptions,
        spec=spec.app,
    )
