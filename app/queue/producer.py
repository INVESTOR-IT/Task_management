from aio_pika import RobustChannel, RobustQueue

import aio_pika

import json
import asyncio

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
            logger.info('Подключение к RabbitMQ')
            try:
                cls._connection = await aio_pika.connect_robust(settings.AMQP_URL)
                cls._channel = await cls._connection.channel()
                logger.info('RabbitMQ подключен')

                for priority in TaskPriority:
                    queue_name = cls._get_queue_name(priority)
                    cls._queues[priority] = cls._channel.declare_queue(
                        queue_name,
                        durable=True
                    )
                    logger.info(f'Объявлена очередь в RabbitMQ: {queue_name}')
            except Exception as err:
                logger.error(f'Не удалось подключиться к RabbitMQ: {err}')
                cls._connection = None
                cls._channel = None
                raise

    @classmethod
    async def disconnect(cls):
        if cls.isconnection():
            await cls._connection.close()
            cls._connection = None
            cls._channel = None
            logger.info('RabbitMQ отключен')

    @staticmethod
    def _get_queue_name(priority: TaskPriority) -> str:
        return f'task_queue_{priority.value.lower()}'

    @classmethod
    async def publish_task_message(cls, task_id: str, priority: TaskPriority):
        if cls.isconnection():
            logger.info('RabbitMQ не активен, выполняется подключение')
            await cls.connect()

        if cls._channel is None:
            logger.info('Не удалось опубликовать сообщение: канал RabbitMQ недоступен.')
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
            aio_pika.Message(
                body=message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue.name
        )
        logger.info(f'Опубликованная задача {task_id} '
                    f'помещена в очередь {queue.name}')



