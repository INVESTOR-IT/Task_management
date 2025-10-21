import asyncio

from app.core.config import logger
from app.db.base import Base
from app.db.database import engine
from app.worker.consumer import run_worker


async def init_db_async():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as db_err:
        logger.error('RabbitMQC: Не удалось инициализировать '
                     f'базу данных: {db_err}', exc_info=True)
        raise


async def main():
    # await init_db_async()
    logger.info('Запуск RabbitMQC')
    await run_worker()


try:
    asyncio.run(main())
except KeyboardInterrupt:
    logger.info('RabbitMQC: Получено прерывание, RabbitMQC завершен')
except Exception as err:
    logger.error(f'RabbitMQC: Ошибка при заупске: {err}', exc_info=True)
