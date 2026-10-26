"""
events.py — Server-Sent Events (SSE) router streaming real-time pipeline events to the UI.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from ai_frappe_builder.events import event_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sessions", tags=["events"])


@router.get("/{session_id}/events")
async def stream_session_events(session_id: str, request: Request) -> EventSourceResponse:
    """
    Subscribes to all real-time events for a generation session via SSE.
    Streams token streams, question prompts, state transitions, validation reports, and patches.
    """

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        logger.info("SSE client connected for session %s", session_id)
        try:
            async for event in event_manager.subscribe(session_id):
                if await request.is_disconnected():
                    logger.info("SSE client disconnected for session %s", session_id)
                    break
                yield event.to_sse_dict()
        except Exception as e:
            logger.warning("Error in event stream for session %s: %s", session_id, e)

    return EventSourceResponse(event_generator())
