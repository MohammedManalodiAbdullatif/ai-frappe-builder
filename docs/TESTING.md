# Testing Strategy & Quality Assurance

AI Frappe App Builder implements a multi-layer verification strategy ensuring both the generator and its output are strictly validated.

## 1. Test Layers

```
Layer 5: LLM Evaluation Harness (`evals/run_evals.py`)
         Measures spec validity rate, healing cycles, cost, and bench pass rates.
   ▲
Layer 4: Golden Spec Exports (`tests/golden/`)
         End-to-end export tests for 5 archetypes (Car Rental, Wholesale, Clinic, School, Field Service).
   ▲
Layer 3: Contract Tests (`tests/contract/`)
         Verifies agent input/output models and API routes with respx mocking.
   ▲
Layer 2: Unit Tests (`tests/unit/`)
         Property-based fuzzing (Hypothesis), schema migration, and 20+ validator rules.
   ▲
Layer 1: Static Type & Style Gates
         `ruff check`, `ruff format`, `mypy --strict`.
```

## 2. Running Test Suites

```bash
# Run all unit, contract, and golden tests
make test

# Run unit tests only
make test-unit

# Run contract tests with mocked LLMs
make test-contract

# Run golden archetype exports
make test-golden

# Run full evaluation benchmark
make eval

# Run frontend test suite
cd frontend && npm test
```

## 3. Containerized Bench Testing (`docker/`)
When Docker is available, `services/bench_runner.py` installs the exported app into a live Frappe v15 container (`test.localhost`), migrates the database, and executes `bench run-tests`.
If Docker CLI is absent, it executes local package AST compilation and JSON schema verification.
