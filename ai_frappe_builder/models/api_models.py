"""
api_models.py — Request and Response models for the AI Frappe Builder REST and SSE API.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ChatStartRequest(BaseModel):
    message: str
    client_name: str = "Frappe Client"
    frappe_url: str = ""
    frappe_api_key: str = ""
    frappe_api_secret: str = ""


class ChatMessageRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    status: str
    questions: list[dict[str, Any]] = []
    assumptions: list[str] = []
    spec: dict[str, Any] | None = None
    interview_turn: dict[str, Any] | None = None
    coverage: dict[str, float] | None = None


class PlanResponse(BaseModel):
    spec: dict[str, Any] | None
    validation: dict[str, Any]
    assumptions: list[str] = []


class ApplyResponse(BaseModel):
    status: str
    created: list[str] = []
    errors: list[str] = []
    preview_urls: list[str] = []
