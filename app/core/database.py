from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# Synchronous Engine and Session
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=3,
    max_overflow=2
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Asynchronous Engine and Session
async_url = settings.ASYNC_DATABASE_URL
connect_args = {}

if "asyncpg" in async_url:
    from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
    parsed = urlparse(async_url)
    query = dict(parse_qsl(parsed.query))
    if "sslmode" in query or "ssl" in parsed.query:
        query.pop("sslmode", None)
        query.pop("channel_binding", None)
        connect_args["ssl"] = True
    new_query = urlencode(query)
    parsed = parsed._replace(query=new_query)
    async_url = urlunparse(parsed)

async_engine = create_async_engine(
    async_url,
    pool_pre_ping=True,
    pool_size=3,
    max_overflow=2,
    connect_args=connect_args
)
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Declarative Base
Base = declarative_base()


# Dependencies for FastAPI Dependency Injection
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
