from aio_pika import RobustChannel, RobustQueue, connect_robust, Message, DeliveryMode

import json, asyncio

from app.models.task import TaskPriority
from app.core.config import logger, settings


class RabbitMQProducer:
    _connection: RobustChannel | None = None
    _channel: RobustChannel | None = None
    _queues: dict[TaskPriority, RobustQueue] = {}

    @classmethod
    def isconnection(cls) -> bool:
        return cls._connection is None or cls._connection.is_closed

    @classmethod
    async def connect(cls):
        if cls.isconnection():
            logger.info('Подключение к RabbitMQP')
            try:
                cls._connection = await connect_robust(settings.AMQP_URL)
                cls._channel = await cls._connection.channel()
                logger.info('RabbitMQP подключен')

                for priority in TaskPriority:
                    queue_name = cls._get_queue_name(priority)
                    cls._queues[priority] = cls._channel.declare_queue(
                        queue_name,
                        durable=True
                    )
                    logger.info(f'Объявлена очередь в RabbitMQP: {queue_name}')
            except Exception as err:
                logger.error(f'Не удалось подключиться к RabbitMQP: {err}')
                cls._connection = None
                cls._channel = None
                raise

    @classmethod
    async def disconnect(cls):
        if not cls.isconnection():
            await cls._connection.close()
            cls._connection = None
            cls._channel = None
            logger.info('RabbitMQP отключен')

    @staticmethod
    def _get_queue_name(priority: TaskPriority) -> str:
        return f'task_queue_{priority.value.lower()}'

    @classmethod
    async def publish_task_message(cls, task_id: str, priority: TaskPriority):
        if cls._channel is None or cls._channel.is_closed:
            logger.info('RabbitMQP не активен, выполняется подключение')
            await cls.connect()

        if cls._channel is None:
            logger.error('Не удалось опубликовать сообщение: канал RabbitMQP недоступен.')
            raise ConnectionError('Канал RabbitMQ недоступен.')

        message_body = json.dumps({'task_id': task_id}).encode('utf-8')
        queue = cls._queues.get(priority)

        if not queue:
            logger.error(f'Очередь на получение приоритета {priority} не найдена')
            await cls.connect()
            queue = cls._queues.get(priority)
            if not queue:
                raise ValueError(
                    f'Очередь на получение приоритета {priority} '
                    'по-прежнему недоступна после повторного подключения.'
                )

        await cls._channel.default_exchange.publish(
            Message(
                body=message_body,
                delivery_mode=DeliveryMode.PERSISTENT
            ),
            routing_key=queue.name
        )
        logger.info(f'Опубликованная задача {task_id} '
                    f'помещена в очередь {queue.name}')


async def main():
    await RabbitMQProducer.connect()
    try:
        await RabbitMQProducer.publish_task_message('123', TaskPriority.HIGH)
        await RabbitMQProducer.publish_task_message('456', TaskPriority.MEDIUM)
    finally:
        await RabbitMQProducer.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
