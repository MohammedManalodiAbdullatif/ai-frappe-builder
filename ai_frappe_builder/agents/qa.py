"""
qa.py — Quality Assurance agent running bench tests and managing error tracebacks.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from ai_frappe_builder.agents.base import BaseAgent
from ai_frappe_builder.services.bench_runner import BenchExecutionResult, BenchRunner

logger = logging.getLogger(__name__)


class QAInput(BaseModel):
    """Input payload to QA agent."""

    app_path: str
    app_name: str


class QAReport(BaseModel):
    """Quality Assurance and bench test execution report."""

    app_name: str
    passed: bool
    execution_mode: str
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    traceback: str | None = None
    output: str = ""
    duration_seconds: float = 0.0


class QAAgent(BaseAgent[QAInput, QAReport]):
    """Runs test suites against exported apps and inspects execution results."""

    name = "qa"
    output_model = QAReport

    def __init__(self, bench_runner: BenchRunner | None = None) -> None:
        super().__init__()
        self.bench_runner = bench_runner or BenchRunner()

    async def run(
        self,
        input_data: QAInput,
        session_id: str | None = None,
        stream_callback: Any | None = None,
    ) -> QAReport:
        result: BenchExecutionResult = self.bench_runner.run_tests(
            app_path=input_data.app_path,
            app_name=input_data.app_name,
        )

        return QAReport(
            app_name=result.app_name,
            passed=result.passed,
            execution_mode=result.execution_mode,
            total_tests=result.total_tests,
            passed_tests=result.passed_tests,
            failed_tests=result.failed_tests,
            traceback=result.traceback,
            output=result.stdout,
            duration_seconds=result.duration_seconds,
        )
