# ADR 0005: Lightweight Typed State Machine Orchestrator vs External Agent Frameworks

## Status
Accepted

## Context
We need to coordinate 10 specialized agent roles (Interviewer, Architect, Differ, Validator, Healer, ScriptWriter, ReportBuilder, Exporter, QA, and Documenter). We evaluated:
1. Heavy external agent frameworks (e.g. LangChain, CrewAI, AutoGen).
2. A bespoke, lightweight typed state-machine orchestrator built on native Python `asyncio`, Pydantic v2 schemas, and explicit state transitions.

## Decision
We chose to build a **Bespoke Typed State Machine Orchestrator** in `agents/orchestrator.py` without heavy third-party agent frameworks.

## Rationale
1. **Deterministic Contracts**: Each agent has an explicit Pydantic v2 `InputModel` and `OutputModel`. There are no hidden string-passing layers, unexpected tool loops, or uncontrollable agent-to-agent chatter.
2. **Predictable State Transitions**: Frappe app generation is a well-defined directed pipeline:
   `discovery -> drafting -> validating -> [healing] -> scripting -> reporting -> exporting -> [testing] -> done`.
   A state machine with explicit guards is vastly more reliable and debuggable than autonomous multi-agent consensus prompts.
3. **Zero Bloat & Direct Observability**: Eliminates thousands of lines of unneeded framework dependencies. Every agent call passes through our central `LLMClient`, emitting structured trace events, prompt hashes, token accounting, and latency directly into SQLite.
4. **Maintenance & Testing**: Mocking agent inputs and outputs in `pytest` with `respx` requires zero framework mocking or monkeypatching.

## Consequences
- The orchestration logic is transparent, explicit, and lives in `agents/orchestrator.py`.
- Adding a new agent requires creating a class inheriting from `BaseAgent`, defining its typed input/output Pydantic models, and registering its prompt in `agents/prompts/`.
