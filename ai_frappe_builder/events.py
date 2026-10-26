"""
events.py — Real-time event publishing and subscription engine for SSE streaming.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

EventType = Literal[
    "token",
    "question",
    "interview_turn",
    "message",
    "state_change",
    "stage_transition",
    "spec_patch",
    "validation",
    "qa_progress",
    "artifact_ready",
    "qa_report",
    "subagent_activity",
    "error",
]


class PipelineEvent(BaseModel):
    """A strongly typed event emitted during app generation."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    event_type: EventType
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    data: dict[str, Any] = Field(default_factory=dict)

    def to_sse_dict(self) -> dict[str, str]:
        return {
            "id": self.event_id,
            "event": self.event_type,
            "data": self.model_dump_json(),
        }


class EventManager:
    """In-memory pub-sub manager distributing events to SSE clients."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[PipelineEvent]]] = defaultdict(set)

    async def publish(
        self,
        session_id: str,
        event_type: EventType,
        data: dict[str, Any],
    ) -> PipelineEvent:
        event = PipelineEvent(session_id=session_id, event_type=event_type, data=data)
        queues = self._subscribers.get(session_id, set())
        for q in list(queues):
            try:
                q.put_nowait(event)
            except Exception as e:
                logger.warning("Failed to deliver event to subscriber: %s", e)
        return event

    async def subscribe(self, session_id: str) -> AsyncIterator[PipelineEvent]:
        q: asyncio.Queue[PipelineEvent] = asyncio.Queue()
        self._subscribers[session_id].add(q)
        try:
            while True:
                event = await q.get()
                yield event
        finally:
            self._subscribers[session_id].discard(q)
            if not self._subscribers[session_id]:
                self._subscribers.pop(session_id, None)


# Global event manager instance
event_manager = EventManager()
