# Specialist Agent Catalog — AI Frappe App Builder

Every specialist agent is an isolated class inheriting from `BaseAgent[InputT, OutputT]`, equipped with an isolated system prompt, strict Pydantic input/output contracts, and execution tracing.

| Agent | Module | Input Contract | Output Contract | Primary Role |
|---|---|---|---|---|
| **Interviewer** | `agents/interviewer.py` | `InterviewInput` | `InterviewTurn` | One-by-one discovery, never silent assumptions, proposes choice options, detects archetype, signals readiness. |
| **Architect** | `agents/architect.py` | `ArchitectInput` | `AppSpecV2` | Synthesizes discovery transcripts into `AppSpec 2.0`, linking to core ERPNext DocTypes instead of duplicating them. |
| **Differ** | `agents/differ.py` | `DifferInput` | `SpecPatch` | Converts natural language change requests into minimal RFC 6902 JSON Patches (`add`, `remove`, `replace`). |
| **Validator** | `validator/rule_engine.py` | `AppSpecV2` | `ValidationReport` | Deterministic (zero-LLM) verification of 20+ Frappe v15 schema rules. |
| **Healer** | `agents/healer.py` | `HealerInput` | `SpecPatch` | Interprets `ValidationReport` and synthesizes surgical RFC 6902 repair patches (max 3 rounds). |
| **ScriptWriter** | `agents/script_writer.py` | `DocTypeSpec` | `GeneratedCode` | Emits AST-verified Python controller methods (`validate`, `before_save`, `on_submit`) and client scripts (`<dt>.js`). |
| **ReportBuilder** | `agents/report_builder.py` | `ReportSpec`, `WorkspaceSpec` | File bundle | Generates Script Reports (`.json`, `.py`, `.js`), Desk Number Cards, Dashboard Charts, and Workspace layouts. |
| **Exporter** | `services/exporter.py` | `AppSpecV2` | Repo & Zip | Canonical `bench new-app` packager, byte-stable DocType JSON, fixture filters, Git commit, `.zip`. |
| **QA** | `agents/qa.py` | `QAInput` | `QAReport` | Generates `FrappeTestCase` suites, runs bench/local test runner, and extracts failure tracebacks. |
| **Documenter** | `agents/documenter.py` | `AppSpecV2` | `DocumentationBundle` | Synthesizes Mermaid ERD diagrams, workflow state charts, and role-based user manuals. |
