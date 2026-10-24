# ADR 0002: SQLite (aiosqlite) vs PostgreSQL for Session and Spec Persistence

## Status
Accepted

## Context
The application needs persistence for:
- Sessions and historical chat turn messages.
- Immutable, versioned snapshots of the AppSpec.
- Agent run tracing (latency, prompt hashes, token usage, cost).
- Artifact metadata and QA test run outcomes.

We must support both zero-configuration local single-developer workflows and multi-tenant hosted environments.

## Decision
We chose **SQLAlchemy 2.0 Async ORM with Alembic migrations**, configured by default to **SQLite via `aiosqlite`** with full configuration support for **PostgreSQL via `asyncpg`**.

## Rationale
1. **Zero-friction Local Startup**: SQLite requires no external database service, Docker containers, credentials, or background daemons. A new developer or evaluator can run `make dev` and have an operational database immediately.
2. **ACID & Concurrent WAL Mode**: In WAL (Write-Ahead Logging) mode with `aiosqlite`, SQLite easily handles concurrent reads while maintaining isolated write transactions.
3. **Seamless Migration to PostgreSQL**: By writing standard SQLAlchemy 2.0 declarative models and managing schema versions through Alembic, switching to a hosted PostgreSQL database requires only changing `DATABASE_URL` in `.env`.
4. **Embedded Footprint**: Session history and generated specs remain portable and can be checked or inspected using standard tools.

## Consequences
- Single-instance deployments run effortlessly on SQLite without container baggage.
- Enterprise/SaaS deployments point `DATABASE_URL` to PostgreSQL without requiring code changes.
- All database operations are strictly async (`AsyncSession`).
