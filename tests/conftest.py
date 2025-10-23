from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from typing import AsyncGenerator
import pytest

from app.core.config import settings
from app.db.base import Base
from app.db.database import get_database
from app.main import app as fastapi_app


TEST_DATABASE_URL = settings.DATABASE_URL.replace('task_management', 'test_db')
test_engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    expire_on_commit=False
)


@pytest.fixture(scope='session', autouse=True)
async def setup_db():
    '''
    Создает таблицы перед всеми тестами сессии и удаляет их после
    '''
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture(scope='function')
async def db_session(setup_db) -> AsyncGenerator[AsyncSession, None]:
    '''
    Создает новую сессию БД для каждого теста 
    и откатывает транзакцию после каждого теста
    '''
    connection = await test_engine.connect()
    transaction = await connection.begin()
    session = TestSessionLocal(bind=connection)

    try:
        yield session
    finally:
        await transaction.rollback()
        await connection.close()
        await session.close()


@pytest.fixture(scope='function', autouse=True)
async def override_get_db(db_session: AsyncSession):
    '''
    Переопределяет зависимость get_database FastAPI 
    для использования тестовой сессии
    '''
    async def _override_get_db():
        yield db_session
    fastapi_app.dependency_overrides[get_database] = _override_get_db
    yield
    fastapi_app.dependency_overrides = {}
