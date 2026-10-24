# ADR 0004: RFC 6902 JSON Patch for Incremental Schema Edits

## Status
Accepted

## Context
When a user asks to modify an existing specification (e.g. *"add an insurance expiry date to Vehicle"* or *"make agreement submittable"*), regenerating the entire `AppSpec` JSON document causes critical problems:
1. High token usage and latency (regenerating 500 lines of JSON for a 1-line change).
2. Hallucination drift: The LLM silently alters previous field names, options, or workflows that the user had already verified.
3. Lack of auditability: Hard to visualize what actually changed between versions.

## Decision
We adopt **RFC 6902 JSON Patch (`jsonpatch`)** as the formal representation for incremental schema mutations produced by the **Differ agent**.

## Rationale
1. **Targeted, Atomic Edits**: A JSON Patch operation explicitly specifies the exact operation (`add`, `remove`, `replace`, `move`, `copy`) and path (e.g., `{"op": "add", "path": "/app/doctypes/0/fields/-", "value": {"fieldname": "insurance_expiry", ...}}`).
2. **Deterministic Application & Inversion**: JSON patches apply cleanly to the in-memory spec using standard RFC 6902 libraries. Rollbacks are trivial because patches can be inverted.
3. **Auditable Version History**: Every version in `spec_versions` stores the parent version ID and the exact JSON Patch that created it.
4. **Optimistic UI Updates**: The frontend can immediately apply the patch to its local state, run client-side validation, and display a visual diff to the user before backend confirmation.

## Consequences
- The Differ agent's output contract is strictly `SpecPatch` (a list of RFC 6902 patch operations).
- The full spec is never re-generated during iteration, preventing regression bugs and conserving LLM tokens.
