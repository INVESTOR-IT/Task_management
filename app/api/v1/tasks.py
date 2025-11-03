from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from uuid import UUID
from typing import Annotated

from app.db.database import get_database
from app.models.task import TaskStatus
from app.schemas.task import (TaskResponse, TaskCreate, TaskStatusResponse,
                              PaginatedTasksResponse, TaskPriority)
from app.servisec.tasks import (create_task_s, get_tasks_s, get_task_s,
                                cancel_task_s, get_task_status_s)

router = APIRouter()


@router.post('/', response_model=TaskResponse, status_code=201)
async def create_task(
    task_in: TaskCreate,
    session: Annotated[AsyncSession, Depends(get_database)]
):
    '''
    Создает новую задачу и отправляет на обработку
    '''

    database_task = await create_task_s(task_in, session)
    return database_task


@router.get('/', response_model=PaginatedTasksResponse)
async def get_tasks(
    session: Annotated[AsyncSession, Depends(get_database)],
    status: TaskStatus | None = Query(
        default=None,
        description='Фильтр по статусу задач'
    ),
    priority: TaskPriority | None = Query(
        default=None,
        description='Филтр по приоритету задач'
    ),
    page: int = Query(default=1, ge=1, description='Номер страницы'),
    page_size: int = Query(
        default=10,
        ge=1,
        le=100,
        description='Количество задач на странице'
    )
):
    '''
    Возвращает список задач с учетом заданных фильтров
    '''

    return await get_tasks_s(session, status, priority, page, page_size)


@router.get('/{task_id}', response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    session: Annotated[AsyncSession, Depends(get_database)]
):
    '''
    Возвращает информацию о конкретной задаче
    '''

    return await get_task_s(task_id, session)


@router.delete('/{task_id}', status_code=204)
async def cancel_task(
    task_id: UUID,
    session: Annotated[AsyncSession, Depends(get_database)]
):
    '''
    Удаляет задачу, если она находится в статусе NEW или PENDING
    '''

    await cancel_task_s(task_id, session)
    return


@router.get('/{task_id}/status', response_model=TaskStatusResponse)
async def get_task_status(
    task_id: UUID,
    session: Annotated[AsyncSession, Depends(get_database)]
):
    '''
    Возвращает текущий статус задачи по ID 
    '''

    return await get_task_status_s(task_id, session)
