"""
Async SQLAlchemy engine & session factory.
Supports SQLite (default) and PostgreSQL.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
from app.config import get_settings

settings = get_settings()

# SQLite needs special config (no pool_size, connect_args for threads)
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = {
    "echo": settings.DEBUG,
}

if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    _engine_kwargs["poolclass"] = StaticPool
else:
    _engine_kwargs["pool_size"] = 20
    _engine_kwargs["max_overflow"] = 10

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_background_db() -> AsyncSession:
    """Create a standalone session for background tasks (not a generator)."""
    return AsyncSessionLocal()


async def init_db():
    """Create all tables (call once at startup)."""
    from app.models import Base as _  # noqa — ensure models are imported
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
