import asyncio

from app.core.config import logger
from app.worker.consumer import run_worker


async def main():
    logger.info('Запуск RabbitMQC')
    await run_worker()


try:
    asyncio.run(main())
except KeyboardInterrupt:
    logger.info('RabbitMQC: Получено прерывание, RabbitMQC завершен')
except Exception as err:
    logger.error(f'RabbitMQC: Ошибка при заупске: {err}', exc_info=True)
