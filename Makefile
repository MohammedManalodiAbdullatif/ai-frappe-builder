.PHONY: help install dev lint format typecheck test test-unit test-contract test-golden bench-test eval clean

PYTHON ?= python3
PIP ?= pip

help:
	@echo "Available commands:"
	@echo "  make install      Install backend and frontend dependencies"
	@echo "  make dev          Start backend and frontend in development mode"
	@echo "  make lint         Run ruff and eslint"
	@echo "  make format       Format code with ruff and prettier"
	@echo "  make typecheck    Run mypy and tsc typecheckers"
	@echo "  make test         Run all unit, contract, and golden tests"
	@echo "  make bench-test   Run bench verification tests inside Docker container"
	@echo "  make eval         Run LLM quality eval harness"
	@echo "  make clean        Clean build artifacts, caches, and temp exports"

install:
	$(PIP) install -e ".[dev]"
	cd frontend && npm install

dev:
	@echo "Starting backend on :8000 and frontend on :3000..."
	(cd ai_frappe_builder && uvicorn main:app --reload --host 0.0.0.0 --port 8000) & \
	(cd frontend && npm run dev) & \
	wait

lint:
	ruff check .
	cd frontend && npm run lint || true

format:
	ruff format .
	cd frontend && npx prettier --write "src/**/*.{ts,tsx,css,json}" 2>/dev/null || true

typecheck:
	mypy ai_frappe_builder
	cd frontend && npx tsc --noEmit

test: test-unit test-contract test-golden

test-unit:
	pytest tests/unit

test-contract:
	pytest tests/contract

test-golden:
	pytest tests/golden

bench-test:
	@if [ -z "$(APP)" ]; then \
		echo "Usage: make bench-test APP=/path/to/exported/app"; \
		exit 1; \
	fi
	$(PYTHON) -m ai_frappe_builder.services.bench_runner $(APP)

eval:
	$(PYTHON) evals/run_evals.py

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	rm -rf frontend/dist /tmp/frappe_exports/
	find . -type d -name "__pycache__" -exec rm -rf {} +
