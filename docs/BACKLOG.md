# Project Backlog & Future Enhancements

This document tracks future features and non-blocking optimizations intentionally deferred to keep v2.0 focused and reliable.

## 1. Bench & CI Enhancements
- **Pre-baked Frappe v15 Docker Image Registry**: Push `frappe/bench:v15-prebaked` to Docker Hub to reduce initial cold-pull bench container startup times under 60 seconds.
- **Multi-Bench Matrix**: Add Frappe v14 backward-compatibility verification target in CI matrix.

## 2. Agent & Architecture Extensions
- **Custom Print Format Synthesizer**: Add a specialized PrintFormat subagent generating Jinja2/HTML responsive invoice and ticket layouts.
- **Webhook Integration Assistant**: Subagent that configures outgoing Frappe Webhooks to external Zapier/Make endpoints based on DocType events.

## 3. UI/UX Refinements
- **Interactive ERD Drag-and-Drop Node Editing**: Allow dragging nodes and double-clicking fields directly on the ERD canvas to prompt the Differ agent for edits.
- **Git Push OAuth Flow**: One-click GitHub repo creation with personal access token / OAuth connection from the UI.
