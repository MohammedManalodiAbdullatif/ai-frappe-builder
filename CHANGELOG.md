# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [2.0.0] - 2026-10-24

### Added
- **Multi-Agent Architecture**: Replaced monolithic planner with 10 specialist subagents (`Interviewer`, `Architect`, `Differ`, `Validator`, `Healer`, `ScriptWriter`, `ReportBuilder`, `Exporter`, `QA`, `Documenter`).
- **AppSpec 2.0 & RFC 6902 Patching**: Versioned contract with JSON Patch diffing (`SpecPatch`) eliminating specification regeneration hallucinations.
- **Deterministic Validator**: Zero-LLM rule engine verifying 20+ Frappe v15 schema rules, reserved names, link targets, and circular dependencies.
- **Frappe v15 Knowledge Catalog**: Authoritative references in `knowledge/` for fieldtypes, standard ERPNext doctypes, conventions, and workflow templates.
- **Canonical Frappe v15 Exporter**: Produces exact `bench new-app` layouts with byte-stable DocType JSON, `fixtures/`, `install.py`, `hooks.py`, Git commits, and downloadable `.zip` bundles.
- **Containerized Bench Runner**: Integrated Docker bench test runner with deterministic local AST and JSON fallback.
- **Three-Panel Redesigned UI**: Modern workspace featuring real-time Server-Sent Events (SSE), Interactive ERD, Form Simulator, Workflows viewer, File Tree/Code viewer, and Audit Inspector.
- **LLM Evaluation Harness**: Benchmark runner testing golden archetypes and outputting dated benchmark reports.
