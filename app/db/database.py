from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

import greenlet

from app.core.config import settings

engine = create_async_engine(
    url=settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False
)
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def get_database():
    database = SessionLocal()
    try:
        yield database
    finally:
        await database.close()
