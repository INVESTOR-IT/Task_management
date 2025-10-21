from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from loguru import logger

from app.db.base import Base
from app.db.database import engine
from app.queue.producer import RabbitMQProducer
from app.core.config import settings
from app.api.v1 import tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('Запуск сервера')
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info('База данных инициализирована')
    except Exception as db_err:
        logger.error(f'Не удалось инициализировать базу данных: {db_err}', exc_info=True)
        raise
    try:
        await RabbitMQProducer.connect()
    except Exception as err:
        logger.error(f'Не удалось подключиться к RabbitMQ во время запуска: {err}')
    yield
    logger.info('Завершение работы сервера')
    await RabbitMQProducer.disconnect()

app = FastAPI(title='Aсинхронный сервис управления задачами',
              openapi_url=f'{settings.API_V1_STR}/openapi.json',
              lifespan=lifespan)

app.include_router(
    tasks.router,
    prefix=f'{settings.API_V1_STR}/tasks',
    tags=['tasks']
)


@app.get('/', include_in_schema=False)
async def root():
    return RedirectResponse(url='/docs')
