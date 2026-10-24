"""
base.py — Generic abstract BaseAgent class for all specialist subagents.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from ai_frappe_builder.llm.client import LLMClient

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def load_agent_prompt(agent_name: str) -> str:
    """Load system prompt markdown for a named agent."""
    prompt_file = PROMPTS_DIR / f"{agent_name}.md"
    if not prompt_file.is_file():
        raise FileNotFoundError(f"System prompt file not found: {prompt_file}")
    with open(prompt_file, encoding="utf-8") as f:
        return f.read().strip()


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """
    Typed base agent with isolated system prompt, structured I/O contract, and retry repair policy.
    """

    name: str
    output_model: type[OutputT]

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()
        self.system_prompt = load_agent_prompt(self.name)

    @abstractmethod
    async def run(
        self,
        input_data: InputT,
        session_id: str | None = None,
        stream_callback: Any | None = None,
    ) -> OutputT:
        """Execute agent task and return typed output model."""
        pass
