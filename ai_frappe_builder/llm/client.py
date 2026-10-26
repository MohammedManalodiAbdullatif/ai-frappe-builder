"""
client.py — Unified LLM client supporting Ollama Cloud, OpenAI, and Anthropic.
Features structured JSON outputs, streaming token callbacks, retry policies, and per-call tracing.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator, Callable
from typing import Any, cast

import httpx
from pydantic import BaseModel

from ai_frappe_builder.config import get_settings
from ai_frappe_builder.llm.tracer import LLMTrace, LLMTracer

logger = logging.getLogger(__name__)


def _strip_thinking_tags(text: str) -> str:
    """Strip <think>...</think> blocks emitted by deep reasoning models."""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return cleaned.strip()


def _extract_json_block(text: str) -> str:
    """Extract first valid JSON object or fenced codeblock from string."""
    cleaned = _strip_thinking_tags(text)
    if "```json" in cleaned:
        start = cleaned.find("```json") + len("```json")
        end = cleaned.find("```", start)
        if end != -1:
            return cleaned[start:end].strip()
    elif "```" in cleaned:
        start = cleaned.find("```") + len("```")
        end = cleaned.find("```", start)
        if end != -1:
            return cleaned[start:end].strip()

    # Search for matching { ... } bounds
    start_brace = cleaned.find("{")
    end_brace = cleaned.rfind("}")
    if start_brace != -1 and end_brace > start_brace:
        return cleaned[start_brace : end_brace + 1].strip()

    return cleaned


class LLMClient:
    """
    Unified high-reliability LLM client.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        tracer: LLMTracer | None = None,
        timeout: float = 90.0,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.get_effective_base_url()).rstrip("/")
        self.api_key = api_key or settings.get_effective_llm_key()
        self.model = model or settings.get_effective_llm_model()
        self.timeout = timeout
        self.tracer = tracer or LLMTracer()

        # Determine backend provider
        if "anthropic.com" in self.base_url:
            self.provider = "anthropic"
        elif "ollama" in self.base_url:
            self.provider = "ollama"
        else:
            self.provider = "openai"

    async def complete(
        self,
        messages: list[dict[str, str]],
        response_schema: type[BaseModel] | dict[str, Any] | None = None,
        stream_callback: Callable[[str], Any] | None = None,
        agent_name: str | None = None,
        session_id: str | None = None,
        temperature: float = 0.2,
        max_retries: int = 3,
    ) -> dict[str, Any] | str:
        """
        Execute completion with retries, structured JSON extraction, and tracing.
        """
        trace = LLMTrace(
            provider=self.provider,
            model=self.model,
            messages=messages,
            session_id=session_id,
            agent_name=agent_name,
        )

        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        # Request JSON mode when schema or structured output is required
        if response_schema:
            payload["response_format"] = {"type": "json_object"}

        endpoint = f"{self.base_url}/chat/completions"

        last_error: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if stream_callback:
                        payload["stream"] = True
                        full_content: list[str] = []
                        async with client.stream(
                            "POST", endpoint, headers=headers, json=payload
                        ) as resp:
                            resp.raise_for_status()
                            async for line in resp.aiter_lines():
                                if not line or not line.startswith("data: "):
                                    continue
                                chunk_str = line[len("data: ") :].strip()
                                if chunk_str == "[DONE]":
                                    break
                                try:
                                    chunk_data = json.loads(chunk_str)
                                    delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                                    token = delta.get("content", "")
                                    if token:
                                        full_content.append(token)
                                        res = stream_callback(token)
                                        if hasattr(res, "__await__"):
                                            await res
                                except Exception:
                                    continue
                        raw_text = "".join(full_content)
                        prompt_tokens = len(str(messages)) // 4
                        completion_tokens = len(raw_text) // 4
                    else:
                        resp = await client.post(endpoint, headers=headers, json=payload)
                        resp.raise_for_status()
                        data = resp.json()
                        choice = data.get("choices", [{}])[0].get("message", {})
                        raw_text = choice.get("content") or choice.get("reasoning_content") or ""
                        usage = data.get("usage", {})
                        prompt_tokens = usage.get("prompt_tokens", len(str(messages)) // 4)
                        completion_tokens = usage.get("completion_tokens", len(raw_text) // 4)

                    trace.complete(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        status="success",
                    )
                    self.tracer.record(trace)

                    if response_schema:
                        extracted = _extract_json_block(raw_text)
                        try:
                            parsed_json = json.loads(extracted)
                            if isinstance(response_schema, type) and issubclass(
                                response_schema, BaseModel
                            ):
                                try:
                                    return response_schema.model_validate(parsed_json).model_dump()
                                except Exception as val_err:
                                    if getattr(response_schema, "__name__", "") == "AppSpecV2":
                                        from ai_frappe_builder.models.migration import migrate_v1_to_v2
                                        return migrate_v1_to_v2(parsed_json).model_dump()
                                    raise val_err
                            return cast(dict[str, Any], parsed_json if isinstance(parsed_json, dict) else {})
                        except json.JSONDecodeError as jde:
                            logger.warning(
                                "Failed to parse JSON response on attempt %d: %s. Raw: %r",
                                attempt,
                                jde,
                                raw_text[:200],
                            )
                            if attempt == max_retries:
                                raise ValueError(f"LLM failed to return valid JSON: {jde}") from jde
                    else:
                        return _strip_thinking_tags(raw_text)

            except Exception as e:
                last_error = e
                logger.warning("LLM call attempt %d failed: %s", attempt, e)
                if attempt < max_retries:
                    err_msg = str(e)
                    payload["messages"] = list(messages) + [
                        {"role": "assistant", "content": raw_text if "raw_text" in locals() else ""},
                        {
                            "role": "user",
                            "content": (
                                f"Your response caused an error: {err_msg}. "
                                "Please fix the issue and return ONLY the valid JSON object adhering strictly to the schema."
                            ),
                        },
                    ]

        trace.complete(status="error", error_message=str(last_error))
        self.tracer.record(trace)
        raise RuntimeError(f"LLM completion failed after {max_retries} attempts: {last_error}")

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        agent_name: str | None = None,
        session_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Async generator streaming raw token chunks."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        endpoint = f"{self.base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", endpoint, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    chunk_str = line[len("data: ") :].strip()
                    if chunk_str == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(chunk_str)
                        delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            yield token
                    except Exception:
                        continue
