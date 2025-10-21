import asyncio

from app.core.config import logger
from app.db.base import Base
from app.db.database import engine
from app.worker.consumer import run_worker

Base.metadata.create_all(bind=engine)
logger.info('Запуск RabbitMQC')

try:
    asyncio.run(run_worker())
except KeyboardInterrupt:
    logger.info('RabbitMQC: Получено прерывание, RabbitMQC завершен')
except Exception as err:
    logger.error(f'RabbitMQC: Ошибка при заупске: {err}', exc_info=True)
