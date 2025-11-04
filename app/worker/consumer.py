from aio_pika import Connection, Channel, connect_robust, IncomingMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import asyncio
import datetime
import json

from app.core.config import logger, settings
from app.models.task import TaskPriority, TaskStatus, Task
from app.db.database import SessionLocal
from app.servisec_worker.processor import process_task_logic


class RabbitMQConsumer:
    _connection: Connection | None = None
    _channel: Channel | None = None
    _consumers: list[asyncio.Task] = []

    @classmethod
    def isconnection(cls) -> bool:
        return cls._connection is None or cls._connection.is_closed

    @classmethod
    async def connect(cls):
        if cls.isconnection():
            try:
                cls._connection = await connect_robust(settings.AMQP_URL)
                cls._channel = await cls._connection.channel()
                logger.info('RabbitMQC подключен')
            except Exception as err:
                logger.error(f'Не удалось подключиться к RabbitMQC: {err}')
                cls._connection = None
                cls._channel = None
                raise

    @classmethod
    async def disconnect(cls):
        if not cls.isconnection():
            for consumer_task in cls._consumers:
                consumer_task.cancel()
            await asyncio.gather(*cls._consumers, return_exceptions=True)
            await cls._connection.close()
            cls._connection = None
            cls._channel = None
            logger.info('RabbitMQC отключен')

    @staticmethod
    def _get_queue_name(priority: TaskPriority) -> str:
        return f'task_queue_{priority.value.lower()}'

    @classmethod
    async def start_consuming(cls):
        if cls._channel is None:
            logger.info('RabbitMQP не активен, выполняется подключение')
            await cls.connect()

        if cls._channel is None:
            logger.error('Не удалось получить сообщение: '
                         'канал RabbitMQP недоступен.')

        for priority_enum in (
            TaskPriority.HIGH,
            TaskPriority.MEDIUM,
            TaskPriority.LOW
        ):
            queue_name = cls._get_queue_name(priority_enum)
            queue = await cls._channel.declare_queue(queue_name, durable=True)
            logger.info(f'Принимаем {queue_name}')
            consumer_task = asyncio.create_task(
                queue.consume(cls._process_message, no_ack=False)
            )
            cls._consumers.append(consumer_task)
        await asyncio.Future()

    @classmethod
    async def _process_message(cls, message: IncomingMessage):
        async with message.process():
            session: AsyncSession = SessionLocal()
            task = None
            try:
                payload = json.loads(message.body.decode())
                task_id = payload.get('task_id')

                if not task_id:
                    logger.error(f'Принял сообщение без task.id: {message.body}')
                    return
                logger.info(f'Принял задачу {task_id} из {message.routing_key}')

                task = await session.execute(select(Task).where(Task.id == task_id))
                task = task.scalar_one_or_none()

                if not task:
                    logger.warning(f'Задачи {task_id} нет в БД. Пропускаю')
                    return
                if task.status in (
                    TaskStatus.COMPLETED,
                    TaskStatus.FAILED,
                    TaskStatus.CANCELLED
                ):
                    logger.info(f'Задача {task_id} не проходит по статусу: '
                                f'{task.status.value}. Проуспкаю')
                    return

                task.status = TaskStatus.IN_PROGRESS
                task.started_at = datetime.datetime.utcnow()
                await session.commit()
                await session.refresh(task)
                success, result_or_error = await process_task_logic(task_id)
                task.completed_at = datetime.datetime.utcnow()

                if success:
                    task.status = TaskStatus.COMPLETED
                    task.result = result_or_error
                    task.error_info = None
                else:
                    task.status = TaskStatus.FAILED
                    task.result = result_or_error
                    task.result = None

                await session.commit()
                await session.refresh(task)
                logger.info(f'Статус задачи {task_id} обновлен до {task.status.value}')

            except json.JSONDecodeError as json_err:
                logger.error('RabbirMQC: Не удалось расшифровать '
                             f'JSON-файл {message.body} - {json_err}')
            except Exception as err:
                logger.error(f'RabbirMQC: В процессе {task_id} произошла '
                             f'ошибка: {err}', exc_info=True)
                if task:
                    task.status = TaskStatus.FAILED
                    task.error_info = f'RabbitMQC: внутренняя ошибка {err}'
                    task.completed_at = datetime.datetime.utcnow()
                    await session.commit()
                    await session.refresh(task)
            finally:
                await session.close()


async def run_worker():
    await RabbitMQConsumer.connect()
    try:
        await RabbitMQConsumer.start_consuming()
    except asyncio.CancelledError:
        logger.info('RabbitMQC не запустился')
    except Exception as err:
        logger.error(f'RabbitMQC произошла ошибка: {err}')
    finally:
        await RabbitMQConsumer.disconnect()
        logger.info('RabbitMQC завершился')
