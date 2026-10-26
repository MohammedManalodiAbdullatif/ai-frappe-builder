"""
database.py — Async SQLAlchemy 2.0 setup plus comprehensive table definitions.

Tables:
  sessions      — one row per client build session
  messages      — full conversation history
  spec_versions — versioned AppSpec snapshots with parent pointers and RFC 6902 patches
  agent_runs    — tracking runs per specialist agent
  artifacts     — exported apps, test suites, generated scripts
  qa_runs       — bench and unit test execution runs
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ai_frappe_builder.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


class Session(Base):
    """One planning/build session per client."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="discovery",
        # discovery | drafting | validating | healing | scripting | reporting | exporting | testing | done | failed
    )
    frappe_url: Mapped[str | None] = mapped_column(String, nullable=True)
    frappe_api_key: Mapped[str | None] = mapped_column(String, nullable=True)
    frappe_api_secret: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Message(Base):
    """Individual chat turn stored for full-context replay to the LLM."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String, nullable=False)  # user | assistant | system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class SpecVersion(Base):
    """Versioned snapshot of the AppSpec with parent pointer and RFC 6902 patch."""

    __tablename__ = "spec_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    parent_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    spec_json: Mapped[str] = mapped_column(Text, nullable=False)
    patch_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    __table_args__ = (UniqueConstraint("session_id", "version", name="uq_session_spec_version"),)


# Legacy alias for backward compatibility
AppSpec = SpecVersion


class AgentRun(Base):
    """Track execution of each specialist agent."""

    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False)
    input_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String, default="success")  # success | failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Artifact(Base):
    """Exported bundles, generated files, diagrams, and logs."""

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    artifact_type: Mapped[str] = mapped_column(String, nullable=False)  # zip | repo | report | diagram
    name: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    meta_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class QARun(Base):
    """Bench and unit test execution results."""

    __tablename__ = "qa_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    test_suite: Mapped[str] = mapped_column(String, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    total_tests: Mapped[int] = mapped_column(Integer, default=0)
    failed_tests: Mapped[int] = mapped_column(Integer, default=0)
    traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Database Initialization & Dependency
# ---------------------------------------------------------------------------


async def init_db() -> None:
    """Create all tables if they don't exist yet."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Convenience CRUD Helpers
# ---------------------------------------------------------------------------


async def create_session(
    db: AsyncSession,
    client_name: str,
    frappe_url: str = "",
    frappe_api_key: str = "",
    frappe_api_secret: str = "",
) -> Session:
    sess = Session(
        id=str(uuid.uuid4()),
        client_name=client_name,
        status="discovery",
        frappe_url=frappe_url,
        frappe_api_key=frappe_api_key,
        frappe_api_secret=frappe_api_secret,
    )
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    return sess


async def get_session(db: AsyncSession, session_id: str) -> Session | None:
    result = await db.execute(select(Session).where(Session.id == session_id))
    return result.scalar_one_or_none()


async def add_message(
    db: AsyncSession,
    session_id: str,
    role: str,
    content: str,
) -> Message:
    msg = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role=role,
        content=content,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_messages(db: AsyncSession, session_id: str) -> list[Message]:
    result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    )
    return list(result.scalars().all())


async def save_app_spec(
    db: AsyncSession,
    session_id: str,
    spec_json: str | dict[str, Any],
    validation_result: str | dict[str, Any] | None = None,
    parent_version_id: str | None = None,
    patch_json: str | dict[str, Any] | None = None,
) -> SpecVersion:
    """Save a new SpecVersion, marking previous ones as not-current."""
    if isinstance(spec_json, dict):
        spec_json = json.dumps(spec_json)
    if isinstance(validation_result, dict):
        validation_result = json.dumps(validation_result)
    if isinstance(patch_json, dict):
        patch_json = json.dumps(patch_json)

    try:
        result = await db.execute(
            select(SpecVersion.version)
            .where(SpecVersion.session_id == session_id)
            .order_by(SpecVersion.version.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        next_version = (latest or 0) + 1

        await db.execute(
            update(SpecVersion).where(SpecVersion.session_id == session_id).values(is_current=False)
        )

        spec = SpecVersion(
            id=str(uuid.uuid4()),
            session_id=session_id,
            parent_version_id=parent_version_id,
            version=next_version,
            spec_json=spec_json,
            patch_json=patch_json,
            validation_result=validation_result,
            is_current=True,
        )
        db.add(spec)
        await db.commit()
        await db.refresh(spec)
        return spec
    except Exception:
        await db.rollback()
        raise


async def get_current_spec(db: AsyncSession, session_id: str) -> SpecVersion | None:
    result = await db.execute(
        select(SpecVersion)
        .where(SpecVersion.session_id == session_id, SpecVersion.is_current == True)  # noqa: E712
        .order_by(SpecVersion.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def update_session_status(db: AsyncSession, session_id: str, status: str) -> None:
    await db.execute(update(Session).where(Session.id == session_id).values(status=status))
    await db.commit()
