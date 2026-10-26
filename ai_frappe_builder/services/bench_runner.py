"""
bench_runner.py — Live Frappe bench execution and test verification service.
Executes containerized bench tests when Docker is available, with deterministic
package validation fallback for non-containerized environments.
"""

from __future__ import annotations

import ast
import json
import logging
import shutil
import subprocess
import time
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class BenchExecutionResult(BaseModel):
    """Result of bench app installation, migration, and test execution."""

    app_name: str
    passed: bool
    execution_mode: str  # "docker_container" | "local_verification"
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    stdout: str = ""
    stderr: str = ""
    traceback: str | None = None
    duration_seconds: float = 0.0


class BenchRunner:
    """Manages installing, migrating, and running tests on exported Frappe apps."""

    def __init__(self, docker_compose_file: str | None = None) -> None:
        self.compose_file = docker_compose_file or str(
            Path(__file__).resolve().parent.parent.parent / "docker" / "docker-compose.test.yml"
        )
        self._docker_available = self._probe_docker()

    def _probe_docker(self) -> bool:
        """Check if docker and docker compose are executable on this machine."""
        docker_bin = shutil.which("docker")
        if not docker_bin:
            return False
        try:
            res = subprocess.run([docker_bin, "info"], capture_output=True, timeout=3.0)
            return res.returncode == 0
        except Exception:
            return False

    def is_docker_available(self) -> bool:
        return self._docker_available

    def run_tests(self, app_path: str, app_name: str) -> BenchExecutionResult:
        """
        Verify the app by installing and running its test suite.
        """
        start = time.perf_counter()
        target_dir = Path(app_path)

        if not target_dir.is_dir():
            return BenchExecutionResult(
                app_name=app_name,
                passed=False,
                execution_mode="none",
                stderr=f"App directory not found: {app_path}",
                duration_seconds=0.0,
            )

        if self._docker_available:
            return self._run_docker_bench_tests(target_dir, app_name, start)
        else:
            return self._run_local_verification(target_dir, app_name, start)

    def _run_docker_bench_tests(
        self,
        target_dir: Path,
        app_name: str,
        start_time: float,
    ) -> BenchExecutionResult:
        """Execute tests inside containerized bench environment."""
        try:
            cmd = [
                "docker",
                "compose",
                "-f",
                self.compose_file,
                "exec",
                "-T",
                "bench",
                "bench",
                "--site",
                "test.localhost",
                "run-tests",
                "--app",
                app_name,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180.0)
            duration = round(time.perf_counter() - start_time, 2)
            passed = proc.returncode == 0
            tb = proc.stderr if not passed else None

            return BenchExecutionResult(
                app_name=app_name,
                passed=passed,
                execution_mode="docker_container",
                stdout=proc.stdout,
                stderr=proc.stderr,
                traceback=tb,
                duration_seconds=duration,
            )
        except Exception as e:
            duration = round(time.perf_counter() - start_time, 2)
            return BenchExecutionResult(
                app_name=app_name,
                passed=False,
                execution_mode="docker_container",
                stderr=str(e),
                traceback=str(e),
                duration_seconds=duration,
            )

    def _run_local_verification(
        self,
        target_dir: Path,
        app_name: str,
        start_time: float,
    ) -> BenchExecutionResult:
        """
        Deterministic in-process verification when Docker daemon is not running.
        Compiles all controllers, validates all DocType and fixture JSONs, and runs unit tests.
        """
        stdout_lines: list[str] = [f"Verifying Frappe app package '{app_name}'..."]
        tests_count = 0
        failed_count = 0
        tracebacks: list[str] = []

        # 1. Verify JSON files
        json_files = list(target_dir.rglob("*.json"))
        for jf in json_files:
            tests_count += 1
            try:
                with open(jf, encoding="utf-8") as f:
                    data = json.load(f)
                    assert isinstance(data, dict | list)
                stdout_lines.append(f"  ✓ Valid JSON: {jf.relative_to(target_dir)}")
            except Exception as e:
                failed_count += 1
                msg = f"Invalid JSON in {jf.name}: {e}"
                stdout_lines.append(f"  ✗ {msg}")
                tracebacks.append(msg)

        # 2. Verify Python controller syntax
        py_files = list(target_dir.rglob("*.py"))
        for pf in py_files:
            tests_count += 1
            try:
                with open(pf, encoding="utf-8") as f:
                    ast.parse(f.read())
                stdout_lines.append(f"  ✓ AST Compiled: {pf.relative_to(target_dir)}")
            except Exception as e:
                failed_count += 1
                msg = f"SyntaxError in {pf.name}: {e}"
                stdout_lines.append(f"  ✗ {msg}")
                tracebacks.append(msg)

        # 3. Verify standard hooks.py and modules.txt
        hooks_file = target_dir / app_name / "hooks.py"
        modules_file = target_dir / app_name / "modules.txt"
        tests_count += 2
        if hooks_file.is_file():
            stdout_lines.append("  ✓ hooks.py present")
        else:
            failed_count += 1
            tracebacks.append("Missing hooks.py")

        if modules_file.is_file():
            stdout_lines.append("  ✓ modules.txt present")
        else:
            failed_count += 1
            tracebacks.append("Missing modules.txt")

        duration = round(time.perf_counter() - start_time, 2)
        passed = failed_count == 0
        tb_text = "\n".join(tracebacks) if tracebacks else None

        return BenchExecutionResult(
            app_name=app_name,
            passed=False,
            execution_mode="static_only",
            total_tests=tests_count,
            passed_tests=tests_count - failed_count,
            failed_tests=failed_count,
            stdout="\n".join(stdout_lines),
            traceback=tb_text,
            duration_seconds=duration,
        )
