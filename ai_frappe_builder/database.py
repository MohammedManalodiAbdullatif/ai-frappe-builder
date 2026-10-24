"""
database.py — Async SQLAlchemy setup plus table definitions.

Tables:
  sessions   — one row per client build session
  messages   — full conversation history (user + assistant turns)
  app_specs  — versioned App Spec snapshots with validation results
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,          # set True to log SQL
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


class Session(Base):
    """One planning/build session per client."""

    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_name = Column(String, nullable=False)
    status = Column(
        String,
        nullable=False,
        default="discovery",
        # valid values: discovery | planned | applying | done | failed
    )
    frappe_url = Column(String, nullable=True)
    frappe_api_key = Column(String, nullable=True)
    frappe_api_secret = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Message(Base):
    """Individual chat turn stored for full-context replay to the LLM."""

    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    role = Column(String, nullable=False)   # "user" | "assistant" | "system"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AppSpec(Base):
    """Versioned snapshot of the App Spec JSON returned by the planner."""

    __tablename__ = "app_specs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    spec_json = Column(Text, nullable=False)          # JSON string
    validation_result = Column(Text, nullable=True)   # JSON string
    is_current = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("session_id", "version", name="uq_session_version"),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def init_db() -> None:
    """Create all tables if they don't exist yet (called at startup)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Convenience CRUD helpers used by planner / routers
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
    db: AsyncSession, session_id: str, role: str, content: str
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
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())


async def save_app_spec(
    db: AsyncSession,
    session_id: str,
    spec_json: str,
    validation_result: str | None = None,
) -> AppSpec:
    """Save a new App Spec version, marking previous ones as not-current."""
    # Fetch latest version number
    result = await db.execute(
        select(AppSpec.version)
        .where(AppSpec.session_id == session_id)
        .order_by(AppSpec.version.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    next_version = (latest or 0) + 1

    # Mark all previous as not current
    await db.execute(
        update(AppSpec)
        .where(AppSpec.session_id == session_id)
        .values(is_current=False)
    )

    spec = AppSpec(
        id=str(uuid.uuid4()),
        session_id=session_id,
        version=next_version,
        spec_json=spec_json,
        validation_result=validation_result,
        is_current=True,
    )
    db.add(spec)
    await db.commit()
    await db.refresh(spec)
    return spec


async def get_current_spec(db: AsyncSession, session_id: str) -> AppSpec | None:
    result = await db.execute(
        select(AppSpec)
        .where(AppSpec.session_id == session_id, AppSpec.is_current == True)  # noqa: E712
        .order_by(AppSpec.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def update_session_status(
    db: AsyncSession, session_id: str, status: str
) -> None:
    await db.execute(
        update(Session).where(Session.id == session_id).values(status=status)
    )
    await db.commit()
