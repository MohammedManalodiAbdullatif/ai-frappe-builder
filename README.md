# AI Frappe App Builder (v2.0)

A multi-agent AI implementation system that converts natural-language business specifications into installable, verifiable Frappe v15 and ERPNext applications.

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![Frappe Target](https://img.shields.io/badge/frappe-v15.0-orange.svg)
![Tests](https://img.shields.io/badge/tests-31%20passed-brightgreen.svg)
![Mypy](https://img.shields.io/badge/mypy-strict%20clean-green.svg)
![Ruff](https://img.shields.io/badge/ruff-clean-green.svg)

---

## 1. Key Features

- **10 Specialist Agents Orchestration**: `Interviewer`, `Architect`, `Differ`, `Validator`, `Healer`, `ScriptWriter`, `ReportBuilder`, `Exporter`, `QA`, and `Documenter`.
- **AppSpec 2.0 Single Source of Truth**: Full schema definition with RFC 6902 JSON Patching (`SpecPatch`) eliminating whole-spec regeneration hallucination drift.
- **Deterministic Validator**: Zero-LLM verification of 20+ Frappe v15 schema rules (reserved names, referential links, child table constraints, workflow transitions, circular link detection).
- **Canonical `bench new-app` Exporter**: Generates byte-stable DocType JSON, `fixtures/`, `install.py`, `hooks.py`, standalone Git repository, and downloadable `.zip` bundles.
- **Containerized Bench & Local Testing**: Docker-compose Frappe v15 bench verification with automatic in-process AST and schema verification fallback.
- **Three-Panel Redesigned UI**: Real-time Server-Sent Events (SSE), Interactive ERD Data Model, Client-Side Desk Form Simulator, Workflows viewer, File Tree/Code viewer, and Audit Inspector.
- **Automated Evaluation Harness**: Benchmark runner with dated JSON reports evaluating validity rates, bench pass rates, and costs.

---

## 2. Architecture Overview

```
                      +------------------------------------+
                      |     Three-Panel React 18 UI        |
                      |     (ERD, Simulator, Tree, SSE)    |
                      +-----------------+------------------+
                                        │ REST & SSE Stream
                                        ▼
                      +------------------------------------+
                      |        FastAPI Orchestrator        |
                      |   State Machine Lifecycle Engine   |
                      +-----------------+------------------+
                                        │ Dispatches tasks
          +-----------------------------+-----------------------------+
          │                             │                             │
          ▼                             ▼                             ▼
   [Interviewer]                  [Architect]                     [Differ]
One-by-one discovery         AppSpec 2.0 Synthesis         RFC 6902 JSON Patches
          │                             │                             │
          ▼                             ▼                             ▼
    [Validator]                      [Healer]                   [ScriptWriter]
Deterministic Rules            Targeted Repairs          Controllers & Client Scripts
          │                             │                             │
          ▼                             ▼                             ▼
  [ReportBuilder]                  [Exporter]                       [QA]
Workspaces & Charts         bench new-app canonical pkg       Bench & Unit Tests
                                        │
                                        ▼
                          +----------------------------+
                          |   Downloadable .zip bundle |
                          |   Standalone Git Repo      |
                          +----------------------------+
```

---

## 3. Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+

### Setup & Launch
```bash
# 1. Clone repository
git clone https://github.com/your-org/ai-frappe-builder.git
cd ai-frappe-builder

# 2. Setup backend
pip install -e ".[dev]"
cp .env.example .env

# 3. Setup frontend
cd frontend
npm install
npm run build
cd ..

# 4. Start services
# Terminal 1: Backend
uvicorn ai_frappe_builder.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev -- --host 0.0.0.0 --port 3000
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 4. Testing & Verification

```bash
# Run all test suites (unit, contract, golden)
make test

# Run unit tests (Hypothesis fuzzing, validator rules)
make test-unit

# Run contract tests (mocked agent I/O contracts)
make test-contract

# Run golden archetype exports (Car Rental, Wholesale, Clinic, School, Field Service)
make test-golden

# Run full evaluation benchmark
make eval

# Run frontend test suite
cd frontend && npm test
```

---

## 5. Documentation Suite

- [Architecture & State Machine Design](docs/ARCHITECTURE.md)
- [Specialist Agents Catalog](docs/AGENTS.md)
- [AppSpec 2.0 Contract & RFC 6902 Patching](docs/SPEC.md)
- [Frappe v15 Deterministic Schema Rules](docs/FRAPPE_RULES.md)
- [Multi-Layer Testing Strategy](docs/TESTING.md)
- [LLM Evaluation Benchmark Harness](docs/EVALS.md)
- [Project Backlog](docs/BACKLOG.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)
- [Changelog](CHANGELOG.md)
