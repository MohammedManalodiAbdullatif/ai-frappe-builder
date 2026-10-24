"""
tracer.py — SQLite per-call LLM tracing recorder.
Logs prompt hashes, token usage, latency, estimated cost, and status.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
import uuid
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Default model pricing per million tokens ($/1M)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gemma4:31b": {"input": 0.20, "output": 0.40},
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
}


class LLMTrace:
    """A record of a single LLM API invocation."""

    def __init__(
        self,
        provider: str,
        model: str,
        messages: list[dict[str, Any]],
        session_id: str | None = None,
        agent_name: str | None = None,
    ) -> None:
        self.trace_id = str(uuid.uuid4())
        self.session_id = session_id
        self.agent_name = agent_name
        self.provider = provider
        self.model = model
        self.start_time = time.perf_counter()
        self.created_at = datetime.now(UTC).isoformat()

        # Compute stable hash of messages
        dumped = json.dumps(messages, sort_keys=True)
        self.prompt_hash = hashlib.sha256(dumped.encode("utf-8")).hexdigest()

        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.latency_ms = 0.0
        self.cost_usd = 0.0
        self.status = "in_progress"
        self.error_message: str | None = None

    def complete(
        self,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        status: str = "success",
        error_message: str | None = None,
    ) -> None:
        self.latency_ms = round((time.perf_counter() - self.start_time) * 1000, 2)
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens
        self.status = status
        self.error_message = error_message

        # Calculate estimated cost
        pricing = MODEL_PRICING.get(self.model, {"input": 0.20, "output": 0.40})
        input_cost = (prompt_tokens / 1_000_000.0) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000.0) * pricing["output"]
        self.cost_usd = round(input_cost + output_cost, 6)


class LLMTracer:
    """Manages recording traces to SQLite database."""

    def __init__(self, db_path: str = "./ai_frappe.db") -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS llm_traces (
                        trace_id TEXT PRIMARY KEY,
                        session_id TEXT,
                        agent_name TEXT,
                        provider TEXT,
                        model TEXT,
                        prompt_hash TEXT,
                        prompt_tokens INTEGER,
                        completion_tokens INTEGER,
                        total_tokens INTEGER,
                        latency_ms REAL,
                        cost_usd REAL,
                        status TEXT,
                        error_message TEXT,
                        created_at TEXT
                    )
                    """
                )
                conn.commit()
        except Exception as e:
            logger.warning("Could not initialize llm_traces table: %s", e)

    def record(self, trace: LLMTrace) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO llm_traces (
                        trace_id, session_id, agent_name, provider, model,
                        prompt_hash, prompt_tokens, completion_tokens,
                        total_tokens, latency_ms, cost_usd, status,
                        error_message, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trace.trace_id,
                        trace.session_id,
                        trace.agent_name,
                        trace.provider,
                        trace.model,
                        trace.prompt_hash,
                        trace.prompt_tokens,
                        trace.completion_tokens,
                        trace.total_tokens,
                        trace.latency_ms,
                        trace.cost_usd,
                        trace.status,
                        trace.error_message,
                        trace.created_at,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.warning("Failed to persist LLM trace: %s", e)
