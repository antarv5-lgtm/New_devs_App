import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)

# Shared across DatabasePool() instances so we don't create a new engine per request.
_shared = {"engine": None, "session_factory": None}


def _build_database_url() -> str:
    url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/propertyflow")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


class DatabasePool:
    def __init__(self):
        self.engine = _shared["engine"]
        self.session_factory = _shared["session_factory"]

    async def initialize(self):
        """Initialize database connection pool (once)"""
        if _shared["session_factory"]:
            self.engine = _shared["engine"]
            self.session_factory = _shared["session_factory"]
            return
        try:
            engine = create_async_engine(
                _build_database_url(),
                pool_size=20,
                max_overflow=30,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False,
            )
            session_factory = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            _shared["engine"] = engine
            _shared["session_factory"] = session_factory
            self.engine = engine
            self.session_factory = session_factory
            logger.info("✅ Database connection pool initialized")
        except Exception as e:
            logger.error(f"❌ Database pool initialization failed: {e}")
            self.engine = None
            self.session_factory = None

    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()

    def get_session(self) -> AsyncSession:
        """Get database session from pool (use with `async with`)"""
        if not self.session_factory:
            raise Exception("Database pool not initialized")
        return self.session_factory()


# Global database pool instance
db_pool = DatabasePool()


async def get_db_session() -> AsyncSession:
    """Dependency to get database session"""
    if not db_pool.session_factory:
        await db_pool.initialize()
    async with db_pool.get_session() as session:
        yield session
        