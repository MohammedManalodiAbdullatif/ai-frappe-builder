"""
routers/plan.py — Retrieve the current App Spec for a session.

GET /plan/{session_id}
  Returns the spec JSON, validation results, and assumptions.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import planner
import validator
from database import get_current_spec, get_db, get_session
from fastapi import APIRouter, Depends, HTTPException
from frappe_client import FrappeClient
from models import PlanResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{session_id}", response_model=PlanResponse)
async def get_plan(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> PlanResponse:
    """
    Retrieve the latest App Spec snapshot for a session along with
    validation results and the assumptions the planner made.
    """
    sess = await get_session(db, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")

    db_spec = await get_current_spec(db, session_id)
    if not db_spec:
        raise HTTPException(status_code=404, detail="No spec found for this session yet.")

    spec_dict = json.loads(db_spec.spec_json)
    assumptions = spec_dict.get("assumptions", [])

    # Validation results (may already be stored)
    if db_spec.validation_result:
        validation = json.loads(db_spec.validation_result)
    else:
        # Run validation on the fly
        from models import AppSpec
        try:
            spec_obj = AppSpec(**spec_dict)
            fc = FrappeClient(
                base_url=sess.frappe_url or "",
                api_key=sess.frappe_api_key or "",
                api_secret=sess.frappe_api_secret or "",
            )
            try:
                async with fc as client:
                    site_ctx = await planner.get_site_context(client)
            except Exception:
                site_ctx = {"doctypes": [], "modules": [], "roles": [], "installed_apps": []}

            is_valid, msgs = validator.validate(spec_obj, site_ctx)
            validation = {
                "valid": is_valid,
                "errors": [m for m in msgs if m.startswith("ERROR:")],
                "warnings": [m for m in msgs if m.startswith("WARNING:")],
            }
        except Exception as exc:
            validation = {"valid": False, "errors": [str(exc)], "warnings": []}

    return PlanResponse(
        spec=spec_dict.get("app"),
        validation=validation,
        assumptions=assumptions,
    )


class UpdatePlanRequest(BaseModel):
    app: dict[str, Any]


@router.put("/{session_id}")
async def update_plan(
    session_id: str,
    body: UpdatePlanRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Update the app specification (e.g. from visual drag-and-drop connections in ERD).
    Validates the modified data model, saves to DB, updates session, and publishes SSE events.
    """
    from ai_frappe_builder.agents.orchestrator import get_or_create_orchestrator_session
    from ai_frappe_builder.events import event_manager
    from ai_frappe_builder.models.app_spec_v2 import AppMetadata, AppSpecV2
    from ai_frappe_builder.validator.rule_engine import validate_spec
    from database import save_app_spec

    sess = await get_session(db, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")

    try:
        app_meta = AppMetadata.model_validate(body.app)
        orch_sess = get_or_create_orchestrator_session(session_id)
        if orch_sess.spec:
            orch_sess.spec.app = app_meta
        else:
            orch_sess.spec = AppSpecV2(status="ready", app=app_meta)

        report = validate_spec(orch_sess.spec)
        orch_sess.validation_report = report

        # Persist to database
        await save_app_spec(
            db,
            session_id,
            orch_sess.spec.model_dump_json(),
            validation_result=json.dumps(report.model_dump()),
        )

        # Publish SSE events
        await event_manager.publish(
            session_id=session_id,
            event_type="spec_patch",
            data={"output": orch_sess.spec.model_dump()},
        )
        await event_manager.publish(
            session_id=session_id,
            event_type="validation",
            data=report.model_dump(),
        )

        return {
            "status": "ok",
            "app": app_meta.model_dump(),
            "validation": report.model_dump(),
        }
    except Exception as exc:
        logger.error("Failed to update plan: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))

