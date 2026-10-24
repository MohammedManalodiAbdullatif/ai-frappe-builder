"""
test_bench_runner.py — Unit tests for BenchRunner and QAAgent verification pipelines.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_frappe_builder.agents.qa import QAAgent, QAInput, QAReport
from ai_frappe_builder.models.migration import migrate_v1_to_v2
from ai_frappe_builder.services.bench_runner import BenchExecutionResult, BenchRunner
from ai_frappe_builder.services.exporter import FrappeAppExporter

GOLDEN_DIR = Path(__file__).resolve().parent.parent / "golden"


def test_bench_runner_detection() -> None:
    runner = BenchRunner()
    # is_docker_available should return a bool without raising
    assert isinstance(runner.is_docker_available(), bool)


def test_bench_runner_local_verification(tmp_path: Path) -> None:
    # Export a valid car rental app
    with open(GOLDEN_DIR / "car_rental.json", encoding="utf-8") as f:
        spec_dict = json.load(f)

    spec = migrate_v1_to_v2(spec_dict)
    exporter = FrappeAppExporter(output_root=str(tmp_path))
    res = exporter.export(spec)

    runner = BenchRunner()
    result = runner.run_tests(app_path=res["app_path"], app_name=res["app_name"])

    assert isinstance(result, BenchExecutionResult)
    assert result.passed is True
    assert result.failed_tests == 0
    assert result.total_tests > 5
    assert result.execution_mode in ("docker_container", "local_verification")


def test_bench_runner_missing_directory() -> None:
    runner = BenchRunner()
    result = runner.run_tests(app_path="/non/existent/path", app_name="ghost_app")
    assert result.passed is False


@pytest.mark.asyncio
async def test_qa_agent_execution(tmp_path: Path) -> None:
    with open(GOLDEN_DIR / "field_service.json", encoding="utf-8") as f:
        spec_dict = json.load(f)

    spec = migrate_v1_to_v2(spec_dict)
    exporter = FrappeAppExporter(output_root=str(tmp_path))
    res = exporter.export(spec)

    agent = QAAgent()
    qa_report = await agent.run(QAInput(app_path=res["app_path"], app_name=res["app_name"]))

    assert isinstance(qa_report, QAReport)
    assert qa_report.app_name == "field_service"
    assert qa_report.passed is True
    assert qa_report.failed_tests == 0
