"""
routers/plan.py — Retrieve the current App Spec for a session.

GET /plan/{session_id}
  Returns the spec JSON, validation results, and assumptions.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import planner
import validator
from database import get_current_spec, get_db, get_session
from frappe_client import FrappeClient
from models import PlanResponse

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
