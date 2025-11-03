from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from uuid import UUID
from datetime import datetime

from app.schemas.task import (TaskCreate, TaskResponse, TaskStatus,
                              TaskPriority, PaginatedTasksResponse, TaskStatusResponse)
from app.models.task import Task
from app.queue.producer import RabbitMQProducer
from app.core.config import logger


async def create_task_s(
        task_in: TaskCreate,
        session: AsyncSession
) -> TaskResponse:
    '''
    Создает новую задачу и отправляет на обработку
    '''
    database_task = Task(
        title=task_in.title,
        description=task_in.description,
        priority=task_in.priority,
        status=TaskStatus.NEW
    )

    session.add(database_task)
    await session.commit()
    await session.refresh(database_task)

    try:
        await RabbitMQProducer.publish_task_message(
            str(database_task.id),
            database_task.priority
        )
        database_task.status = TaskStatus.PENDING
        await session.commit()
        await session.refresh(database_task)

    except Exception as err:
        logger.error('Не удалось опубликовать задачу '
                     f'{database_task.id} в RabbitMQ: {err}')
        database_task.status = TaskStatus.FAILED
        database_task.error_info = f'Не удалось поставить задачу в очередь: {err}'
        await session.commit()
        await session.refresh(database_task)
        raise HTTPException(
            status_code=500,
            detail=f'Не удалось поставить задачу в очередь {err}'
        )
    return database_task


async def get_tasks_s(
        session: AsyncSession,
        status: TaskStatus,
        priority: TaskPriority,
        page: int,
        page_size: int
) -> PaginatedTasksResponse:
    '''
    Возвращает список задач с учетом заданных фильтров
    '''

    statement = select(Task)
    count_statement = select(func.count(Task.id))

    if status:
        statement = statement.where(Task.status == status)
        count_statement = count_statement.where(Task.status == status)
    if priority:
        statement = statement.where(Task.priority == priority)
        count_statement = count_statement.where(Task.priority == priority)

    statement = (statement.order_by(desc(Task.created_at))
                 .offset((page - 1) * page_size)
                 .limit(page_size)
                 )
    tasks = (await session.execute(statement)).scalars().all()
    total_tasks = (await session.execute(count_statement)).scalar_one()

    return PaginatedTasksResponse(
        total=total_tasks,
        page=page,
        page_size=page_size,
        items=[TaskResponse.model_validate(task) for task in tasks]
    )


async def get_task_s(task_id: UUID, session: AsyncSession) -> TaskResponse:
    '''
    Возвращает информацию о конкретной задаче
    '''

    task = await session.execute(select(Task).where(Task.id == task_id))
    task = task.scalar_one_or_none()

    if task is None:
        raise HTTPException(status_code=404, detail='Такой задачи нет')

    return task


async def cancel_task_s(task_id: UUID, session: AsyncSession) -> None:
    '''
    Удаляет задачу, если она находится в статусе NEW или PENDING
    '''

    task = await session.execute(select(Task).where(Task.id == task_id))
    task = task.scalar_one_or_none()

    if task is None:
        raise HTTPException(status_code=404, detail='Такой задачи нет')

    if task.status in (TaskStatus.NEW, TaskStatus.PENDING):
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.utcnow()
        task.error_info = 'Задание было отменено пользователем'
        await session.commit()
    elif task.status == TaskStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400,
            detail='Задача в данный момент выполняется и не может быть отменена'
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=(
                f'Задача со статусом {task.status.value} не может быть отменена'
            )
        )


async def get_task_status_s(
        task_id: UUID,
        session: AsyncSession
) -> TaskStatusResponse:
    '''
    Возвращает текущий статус задачи по ID 
    '''

    task = await session.execute(select(Task).where(Task.id == task_id))
    task = task.scalar_one_or_none()

    if task is None:
        raise HTTPException(status_code=404, detail='Такой задачи нет')

    return task
