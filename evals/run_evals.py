"""
run_evals.py — Automated quality evaluation harness for AI Frappe App Builder.
Runs golden business requirements through discovery, architecture, validation,
healing, and bench verification, producing dated benchmark reports.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from ai_frappe_builder.models.migration import migrate_v1_to_v2
from ai_frappe_builder.services.bench_runner import BenchRunner
from ai_frappe_builder.services.exporter import FrappeAppExporter
from ai_frappe_builder.validator.rule_engine import validate_spec

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evals")

GOLDEN_DIR = Path(__file__).resolve().parent.parent / "tests" / "golden"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def run_benchmark() -> dict[str, any]:
    """Execute evaluation benchmark across all golden archetypes."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    golden_files = list(GOLDEN_DIR.glob("*.json"))

    logger.info("Found %d golden archetypes to evaluate.", len(golden_files))

    start_time = time.perf_counter()
    bench_runner = BenchRunner()
    results = []

    total_specs = len(golden_files)
    valid_count = 0
    passed_bench_count = 0

    for gf in sorted(golden_files):
        archetype_name = gf.stem
        logger.info("Evaluating archetype: %s", archetype_name)

        with open(gf, encoding="utf-8") as f:
            raw = json.load(f)

        spec = migrate_v1_to_v2(raw)

        # 1. Validation evaluation
        report = validate_spec(spec)
        is_valid = report.is_valid
        if is_valid:
            valid_count += 1

        # 2. Export & Bench evaluation
        tmp_export_dir = Path("/tmp/eval_exports") / archetype_name
        exporter = FrappeAppExporter(output_root=str(tmp_export_dir))
        export_res = exporter.export(spec)

        bench_res = bench_runner.run_tests(
            app_path=export_res["app_path"],
            app_name=export_res["app_name"],
        )
        if bench_res.passed:
            passed_bench_count += 1

        results.append({
            "archetype": archetype_name,
            "valid": is_valid,
            "errors": report.errors,
            "warnings": report.warnings,
            "bench_passed": bench_res.passed,
            "bench_mode": bench_res.execution_mode,
            "total_bench_tests": bench_res.total_tests,
            "duration_sec": bench_res.duration_seconds,
        })

    total_duration = round(time.perf_counter() - start_time, 2)
    validity_rate = round((valid_count / total_specs) * 100, 1) if total_specs else 0.0
    bench_pass_rate = round((passed_bench_count / total_specs) * 100, 1) if total_specs else 0.0

    summary = {
        "benchmark_timestamp": datetime.now(UTC).isoformat(),
        "total_archetypes": total_specs,
        "spec_validity_rate_pct": validity_rate,
        "bench_pass_rate_pct": bench_pass_rate,
        "total_duration_sec": total_duration,
        "results": results,
    }

    # Save dated report
    date_str = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S")
    report_file = RESULTS_DIR / f"eval_{date_str}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info("Evaluation complete! Validity: %.1f%%, Bench Pass: %.1f%%. Report: %s",
                validity_rate, bench_pass_rate, report_file)

    return summary


if __name__ == "__main__":
    res = run_benchmark()
    if res["spec_validity_rate_pct"] < 100.0 or res["bench_pass_rate_pct"] < 100.0:
        logger.error("Quality gate failed: Archetype evaluation not 100% green.")
        sys.exit(1)
    logger.info("All quality gates passed!")
    sys.exit(0)
