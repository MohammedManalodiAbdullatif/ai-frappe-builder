# Rebuild Plan: Production-Grade Multi-Agent Frappe App Generator

**Author:** Staff Engineer & Product Designer  
**Status:** Phase 0 Completed — Ready for Approval  
**Target:** Frappe v15 / ERPNext v15 Production-Grade App Implementer  

---

## 1. Executive Summary & Codebase Audit Findings

A thorough audit of the repository (`Ai_Frappe/`) was conducted. Below are the findings, baseline verifications, and specific notes where current reality intersects with the prompt's assumptions:

### Codebase Audit Summary
1. **Repository Layout**:
   - `ai_frappe_builder/`: Single FastAPI service with monolithic `planner.py` handling chat, prompt formatting, parsing, and auto-healing.
   - `exporter.py`: Emitted minimal DocType `.json`/`.py`, basic `hooks.py`, and `modules.txt`. Lacked `install.py`, `uninstall.py`, `patches.txt`, `fixtures/` with export filters, workspace layouts, and client scripts.
   - `validator.py`: Had basic validation rules; standard ERPNext entities (`Customer`, `Company`, `Supplier`, etc.) were missing from its built-in knowledge.
   - `snippets/`: Contained 7 server script patterns in Python files with string formatting, but lacked a machine-readable schema registry (`registry.yaml`).
   - `frontend/`: Basic React 18 + Vite setup. Lacked a design system, Tailwind, shadcn/ui components, interactive ERD, form preview simulator, and SSE streaming.
2. **Git Repository Status**:
   - The workspace was **not initialized as a git repository**.
   - An active `.env` file containing an API key existed without a `.gitignore`.
   - **Action Taken in Phase 0**: Initialized Git at the repository root (`main` branch) and created a comprehensive `.gitignore` preventing secrets, local databases, and temporary export directories from ever being tracked.
3. **Local Tooling & Environment Findings**:
   - **Python Version**: `3.13.11` is active (satisfies `>=3.11`).
   - **Linters / Testing Tools**: `ruff`, `mypy`, and `pytest` were not yet installed in the local environment. Phase 0 configures `pyproject.toml`, `Makefile`, and dev dependencies.
   - **Docker Host Status**: The `docker` CLI is **not currently installed in the host's PATH** on this macOS machine.
   - **Bench Strategy**: The `services/bench_runner.py` service will support an automated Docker runner with mock/remote fallback. Full containerized bench tests will run natively in `.github/workflows/ci.yml` where Docker is provided by GitHub Actions runners, and locally whenever Docker/Colima is installed.

---

## 2. Target Architecture

```
                                  [ Browser / Client ]
                                           │
                        ┌──────────────────┴──────────────────┐
                        │                                     │
                 (REST Mutations)                     (SSE Event Stream)
                        │                                     │
                        ▼                                     ▼
                  [FastAPI Gateway] <══════════════ [Event Broadcaster]
                        │                                     ▲
                        ▼                                     │
             [Orchestrator State Machine] ────────────────────┘
         (discovery -> drafting -> validating -> healing -> 
          scripting -> reporting -> exporting -> testing -> done)
                        │
       ┌────────────────┴────────────────────────┐
       ▼                                         ▼
[Specialist Subagents]                  [Deterministic Engines]
├── Interviewer (One-by-one discovery)  ├── Knowledge Base (YAML/JSON)
├── Architect (AppSpec 2.0 generator)   ├── Validator Engine (20+ rules)
├── Differ (RFC 6902 JSON Patch)        ├── Exporter (Canonical Frappe v15)
├── Healer (Auto-repair patcher)        └── Bench Runner (Docker / CI)
├── ScriptWriter (AST-checked Python/JS)
├── ReportBuilder (Reports & Dashboards)
├── QA (FrappeTestCase synthesis)
└── Documenter (Mermaid ERD & Guides)
       │
       ▼
 [LLMClient] (Ollama Cloud / OpenAI / Anthropic + Tracing in SQLite)
```

---

## 3. Detailed Phase Breakdown

### Phase 0 — Audit, Governance, Baseline Setup (Completed)
- [x] Initialized Git repository with `main` branch.
- [x] Created root `.gitignore` protecting secrets, `.env`, `*.db`, and build artifacts.
- [x] Created root `pyproject.toml` with `ruff` and `mypy` strict configurations.
- [x] Created root `Makefile` covering all targets (`install`, `dev`, `lint`, `format`, `typecheck`, `test`, `bench-test`, `eval`).
- [x] Configured GitHub Actions CI workflow in `.github/workflows/ci.yml`.
- [x] Authored 5 Architecture Decision Records (ADRs):
  - `docs/adr/0001-sse-vs-websocket.md`
  - `docs/adr/0002-sqlite-vs-postgres.md`
  - `docs/adr/0003-controller-code-vs-server-scripts.md`
  - `docs/adr/0004-json-patch-for-diffs.md`
  - `docs/adr/0005-agent-framework-choice.md`
- [x] Authored comprehensive `PLAN.md` (this document).

---

### Phase 1 — Knowledge Base, AppSpec 2.0, Validator Engine, Unit Tests
**Objective**: Build a deterministic foundation with zero LLM dependencies.

1. **Frappe v15 Knowledge Base (`knowledge/`)**:
   - `knowledge/fieldtypes.yaml`: All 33 Frappe fieldtypes with allowed options, constraints, and validation rules.
   - `knowledge/erpnext_doctypes.yaml`: Curated catalog of standard ERPNext DocTypes, key fields, and relationship requirements.
   - `knowledge/conventions.yaml`: Title Case patterns, naming series formats (`^[A-Z]{2,10}(-\..*)?-\.##+$`), and permission matrix defaults.
   - `knowledge/workflow_templates.yaml`: Idiomatic 3-state and 4-state approval lifecycles.
2. **AppSpec 2.0 Contract (`ai_frappe_builder/models/`)**:
   - Versioned specification (`spec_version: "2.0"`).
   - Strict Pydantic v2 schemas: `DocTypeSpec`, `FieldSpec`, `PermissionSpec`, `WorkflowSpec`, `ServerScriptSpec`, `ClientScriptSpec`, `ReportSpec`, `DashboardSpec`, `WorkspaceSpec`.
   - Migration utility (`ai_frappe_builder/models/migration.py`): Converts legacy 1.0 specs to 2.0 with backward compatibility.
   - Export JSON Schema to `schemas/appspec-2.0.json`.
3. **Deterministic Validator Engine (`ai_frappe_builder/validator/`)**:
   - Replace monolithic validator with a modular rule engine (`rule_engine.py`):
     - Reserved fieldnames, Title Case naming, fieldtype/option matrix validation.
     - Link target existence (checking local spec + `knowledge/erpnext_doctypes.yaml`).
     - Child table referential integrity (`istable=1` and referenced by at least one `Table` field).
     - Section/Column/Tab Break placement rules.
     - Submittable consistency (`is_submittable=1` matches workflow doc_status transitions).
     - Circular dependency detection.
   - Emits structured `ValidationReport{errors: list[str], warnings: list[str], fix_hints: list[dict]}`.
4. **Unit Test Suite**:
   - `tests/unit/test_validator.py`: Property-based testing with `hypothesis` fuzzing invalid schemas.
   - `tests/unit/test_migration.py`: 1.0 to 2.0 conversion tests.
   - `tests/unit/test_knowledge.py`: Schema validation of knowledge base YAML files.

---

### Phase 2 — LLM Client, Specialist Agents, Orchestrator, SSE Streaming & Persistence
**Objective**: Replace the single planner with a multi-agent orchestrator and real-time streaming.

1. **Unified LLM Client (`ai_frappe_builder/llm/client.py`)**:
   - Unified interface supporting Ollama Cloud (`https://ollama.com/v1`), OpenAI, and Anthropic.
   - Structured JSON output enforcement (`response_format={"type": "json_object"}`).
   - Streaming generator mode (`stream_chat()`) emitting token-by-token callbacks.
   - SQLite tracing recorder logging prompt hashes, token usage, latency, and costs per call.
2. **Specialist Agents (`ai_frappe_builder/agents/`)**:
   - `base.py`: Abstract `BaseAgent[InputT, OutputT]` with typed Pydantic models.
   - `prompts/<agent>.md`: Isolated system prompt markdown documents.
   - **Interviewer**: Conducts one-by-one discovery without silent assumptions; returns `InterviewTurn`.
   - **Architect**: Translates requirements into `AppSpec 2.0` referencing knowledge base.
   - **Differ**: Translates natural language change requests into RFC 6902 `SpecPatch` (JSON Patch).
   - **Healer**: Takes `ValidationReport` and produces targeted `SpecPatch` repairs (max 3 rounds).
3. **Orchestrator State Machine (`ai_frappe_builder/agents/orchestrator.py`)**:
   - States: `discovery -> drafting -> validating -> healing -> scripting -> reporting -> exporting -> testing -> done | failed`.
   - Enforces transition guards, retry budgets, and error routing.
4. **Server-Sent Events (SSE) Engine (`ai_frappe_builder/routers/events.py`)**:
   - `GET /api/v1/sessions/{id}/events` streaming typed events: `token`, `question`, `state_change`, `spec_patch`, `validation`, `qa_progress`, `artifact_ready`, `error`.
5. **Database & Alembic Migrations (`ai_frappe_builder/database/`)**:
   - SQLAlchemy 2.0 async models: `Session`, `Message`, `SpecVersion` (parent pointer + patch), `AgentRun`, `Artifact`, `QARun`.
   - Alembic migration scripts.
6. **Contract Tests (`tests/contract/`)**:
   - Round-trip serialization tests for all agent input/output models.
   - `respx`-mocked tests for API routes.

---

### Phase 3 — ScriptWriter, ReportBuilder, Complete Exporter & Golden Specs
**Objective**: Produce fully idiomatic, verifiable Frappe v15 app packages.

1. **Snippet Registry (`ai_frappe_builder/snippets/registry.yaml`)**:
   - Reusable Frappe script patterns with parameter schemas and unit test templates.
2. **ScriptWriter Agent (`ai_frappe_builder/agents/script_writer.py`)**:
   - Synthesizes Python controller logic into `<doctype>.py` methods (`validate`, `before_save`, `on_submit`, `on_cancel`).
   - Synthesizes client scripts into `<doctype>.js`.
   - Verifies Python code with `ast.parse` and formats with `ruff format`.
   - Verifies JavaScript code with parser checks.
3. **ReportBuilder Agent (`ai_frappe_builder/agents/report_builder.py`)**:
   - Emits Script Reports (`report/<name>/<name>.json` + `<name>.py`), Query Reports, Number Cards, Dashboard Charts, and Workspace layouts.
4. **Complete Exporter (`ai_frappe_builder/services/exporter.py`)**:
   - Canonical `bench new-app` layout:
     - Root: `pyproject.toml`, `setup.py`, `README.md`, `license.txt`, `.gitignore`, `.pre-commit-config.yaml`.
     - App root: `__init__.py`, `hooks.py`, `modules.txt`, `patches.txt`, `install.py`, `uninstall.py`, `api.py`, `tasks.py`.
     - Modules: `<module>/doctype/<dt>/{__init__.py, <dt>.json, <dt>.py, <dt>.js, test_<dt>.py}`.
     - Fixtures: `fixtures/` with `hooks.py` fixture export filters.
     - Workspaces & Reports.
   - Canonical DocType JSON field order mirroring `frappe.modules.export_file`.
   - Exposes `GET /api/v1/export/{id}/tree` and `GET /api/v1/export/{id}/file?path=`.
5. **Golden Spec Test Suite (`tests/golden/`)**:
   - Golden archetypes: Car Rental, B2B Wholesale, Medical Clinic, School Academy, Field Service.
   - Tests verify exact file trees, JSON validity, and controller compilation.

---

### Phase 4 — Bench Docker Runner, QA Agent & Live Verification Loop
**Objective**: Guarantee that generated apps actually install and run in a live Frappe bench.

1. **Docker Bench Environment (`docker/`)**:
   - `docker/docker-compose.test.yml`: Spins up MariaDB 10.6, Redis Cache/Queue, and Frappe v15 bench.
   - Dockerfile caching Frappe v15 base layers for sub-3-minute run times.
2. **Bench Runner Service (`ai_frappe_builder/services/bench_runner.py`)**:
   - CLI & library interface: `bench get-app`, `bench install-app`, `bench migrate`, `bench run-tests`.
   - Automatic environment probe: Detects local Docker host vs CI environment; provides mock execution when Docker CLI is absent.
3. **QA Agent (`ai_frappe_builder/agents/qa.py`)**:
   - Synthesizes `test_<dt>.py` (`FrappeTestCase`) with document creation, submission, and workflow transition tests.
   - Executes tests through `bench_runner` and parses test tracebacks.
   - Self-healing loop: On test failure, loops traceback back to Healer/ScriptWriter (max 3 rounds).

---

### Phase 5 — Frontend Redesign (Three-Panel Workspace)
**Objective**: Build a high-performance, polished developer experience.

1. **Design System & Tokens (`frontend/DESIGN.md`, Tailwind CSS)**:
   - Modern, restrained UI direction (Tailwind + shadcn/ui primitives).
   - Typography: Plus Jakarta Sans (UI) + JetBrains Mono (Code/Spec).
   - Theme: Light/Dark mode via CSS variables, 4px spacing grid, 8px radii.
2. **Three-Panel Layout**:
   - **Left Panel (Conversation)**: Streamed messages, question cards with interactive option pills, assumption chips, orchestrator progress stepper, token meter.
   - **Centre Panel (Workbench)**:
     - **Data Model (ERD)**: Interactive graph using React Flow (nodes for DocTypes, edges for Links/Tables; click to inspect and edit).
     - **Form Preview Simulator**: Client-side Frappe Desk form emulator (sections, columns, tabs, link pickers, child grids, validation styling).
     - **Workflows**: State diagram with transitions and role gates.
     - **Code**: Virtualized file tree and code viewer with syntax highlighting and diff view.
     - **Spec JSON**: Schema-aware collapsible viewer.
   - **Right Panel (Inspector)**:
     - Real-time validation report with "Apply Fix" action buttons.
     - Live bench test output stream.
     - Version history with point-in-time restore.
     - One-click "Download App (.zip)" and GitHub push.
3. **Frontend Testing**: Vitest + React Testing Library for components; Playwright e2e test suite.

---

### Phase 6 — LLM Evals, Documentation Suite & Quality Gates
**Objective**: Ensure measurable output quality, complete docs, and clean quality gates.

1. **LLM Evaluation Harness (`evals/`)**:
   - `evals/run_evals.py`: Runs the full pipeline on golden requirements across supported models.
   - Tracks: Spec validity rate, healing rounds, bench pass rate, cost, and question count.
   - Generates dated benchmark reports in `evals/results/<date>.json`.
2. **Complete Documentation Suite**:
   - `README.md`, `docs/ARCHITECTURE.md`, `docs/AGENTS.md`, `docs/SPEC.md`, `docs/FRAPPE_RULES.md`, `docs/TESTING.md`, `docs/EVALS.md`.
   - `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`.
3. **Final Quality Audit**:
   - `ruff check .` and `ruff format --check .` 100% clean.
   - `mypy --strict` 100% clean on `ai_frappe_builder`.
   - `eslint` and `tsc --noEmit` 100% clean on `frontend`.
   - Coverage: `>=85%` backend, `>=70%` frontend.

---

## 4. File-by-File Changes Matrix

| File Path | Action | Description |
|---|---|---|
| `.gitignore` | Created (Phase 0) | Protects secrets, `.env`, `.db`, node_modules, build outputs |
| `pyproject.toml` | Created (Phase 0) | Ruff, Mypy, Pytest configurations and package metadata |
| `Makefile` | Created (Phase 0) | Central build and test automation |
| `.github/workflows/ci.yml` | Created (Phase 0) | GitHub Actions CI pipeline |
| `docs/adr/0001-0005*.md` | Created (Phase 0) | 5 Architecture Decision Records |
| `PLAN.md` | Created (Phase 0) | This comprehensive rebuild plan |
| `knowledge/*.yaml` | Create (Phase 1) | Frappe v15 fieldtypes, ERPNext doctypes, conventions, workflows |
| `ai_frappe_builder/models/` | Create/Refactor (Phase 1) | AppSpec 2.0, Pydantic v2 schemas, migration from 1.0 |
| `ai_frappe_builder/validator/` | Refactor (Phase 1) | Modular deterministic rule engine emitting `ValidationReport` |
| `ai_frappe_builder/llm/client.py` | Create (Phase 2) | Unified Ollama/OpenAI/Anthropic client with streaming & tracing |
| `ai_frappe_builder/agents/` | Create (Phase 2) | Orchestrator, Interviewer, Architect, Differ, Healer |
| `ai_frappe_builder/database/` | Refactor (Phase 2) | SQLAlchemy 2.0 models + Alembic migrations |
| `ai_frappe_builder/routers/` | Refactor (Phase 2) | Versioned `/api/v1` routes with SSE event stream |
| `ai_frappe_builder/snippets/registry.yaml` | Create (Phase 3) | Structured metadata registry for Frappe script patterns |
| `ai_frappe_builder/agents/script_writer.py` | Create (Phase 3) | Controller `<doctype>.py` and client script synthesizer |
| `ai_frappe_builder/agents/report_builder.py` | Create (Phase 3) | Script reports, Query reports, Number Cards, Dashboards |
| `ai_frappe_builder/services/exporter.py` | Refactor (Phase 3) | Canonical Frappe v15 app packager with git & zip |
| `tests/golden/` | Create (Phase 3) | 5 golden archetype requirements and snapshot tests |
| `docker/` | Create (Phase 4) | Frappe v15 bench compose setup |
| `ai_frappe_builder/services/bench_runner.py`| Create (Phase 4) | Executes bench tests inside container / mock fallback |
| `ai_frappe_builder/agents/qa.py` | Create (Phase 4) | Synthesizes `FrappeTestCase` and drives bench verification |
| `frontend/src/` | Full Redesign (Phase 5) | Three-panel workspace, ERD React Flow, Form Simulator, SSE |
| `evals/` | Create (Phase 6) | Pipeline benchmark and accuracy scoring harness |
| `docs/*.md` | Create (Phase 6) | Full documentation suite |

---

## 5. Comprehensive Risk Matrix

| Risk | Impact | Likelihood | Mitigation Strategy |
|---|---|---|---|
| **LLM Output Formatting Drift** | High | Medium | Enforce `response_format={"type": "json_object"}` across all calls. Use Pydantic v2 validation with `auto_heal_spec` repair loops. |
| **Incremental Edit Schema Drift** | High | Medium | Use RFC 6902 JSON Patch (`SpecPatch`) via the Differ agent rather than whole-spec regeneration. |
| **Docker Unavailable on Local Host** | Medium | High | `bench_runner.py` includes host environment detection. If Docker is absent, it runs unit/contract/golden tests locally while gating container tests to CI. |
| **Frappe v15 API Incompatibilities** | High | Low | Validate against official Frappe v15 source. Code is generated into native controller classes, avoiding disabled server script environments. |
| **Streaming Network Disconnections** | Medium | Low | SSE client implementation uses automatic reconnection with `Last-Event-ID` tracking and state re-sync. |
| **Token Cost in Extended Multi-turn Sessions** | Medium | Medium | Track prompt token budgets per agent, trim message histories with state summaries, and log token costs per call in SQLite. |

---

## 6. Phase 0 Verification Status

- **Git Repository**: Initialized (`main` branch) with verified `.gitignore` protecting secrets.
- **Tooling Configuration**: `pyproject.toml`, `Makefile`, and `.github/workflows/ci.yml` in place.
- **Architectural Alignment**: 5 ADRs drafted and committed.
- **Readiness**: All prerequisites for Phase 1 are in place.

**Awaiting user approval of `PLAN.md` before commencing Phase 1.**
