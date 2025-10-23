from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from httpx import AsyncClient

from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.schemas.task import TaskStatus, TaskPriority
from app.models.task import Task


@pytest.mark.asyncio
async def test_create_task(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_rabbitmq_producer: AsyncMock
):
    response = await client.post(
        url='/api/v1/tasks',
        json={
            'title': 'Тестовая задача',
            'description': 'Создаем тестовое задание',
            'priority': TaskPriority.HIGH.value
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data['title'] == 'Тестовая задача'
    assert data['description'] == 'Создаем тестовое задание'
    assert data['priority'] == TaskStatus.PENDING.value
    assert data['status'] == TaskStatus.PENDING.value
    assert 'id' in data
    assert 'created_at' in data
    assert 'updated_at' in data

    task_in_db = await db_session.execute(
        select(Task).where(Task.id == UUID(data['id']))
    )
    task_in_db = task_in_db.scalar_one_or_none()


@pytest.mark.asyncio
async def test_get_tasks_list(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_rabbitmq_producer: AsyncMock
):
    task1 = Task(
        id=UUID('a0000000-0000-0000-0000-000000000001'),
        title='Задача 1',
        priority=TaskPriority.HIGH,
        status=TaskStatus.COMPLETED
    )
    task2 = Task(
        id=UUID('a0000000-0000-0000-0000-000000000002'),
        title='Задача 2',
        priority=TaskPriority.LOW,
        status=TaskStatus.PENDING
    )
    db_session.add_all([task1, task2])
    await db_session.commit()

    response = await client.get('/api/v1/tasks')
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 2
    assert len(data['items']) == 2
    assert data['items'][0]['title'] == 'Задача 2'
    assert data['items'][1]['title'] == 'Задача 1'

    response = await client.get('/api/v1/tasks?status=COMPLETED')
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 1
    assert data['items'][0]['title'] == 'Задача 1'


@pytest.mark.asyncio
async def test_get_single_task(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_rabbitmq_producer: AsyncMock
):
    task = Task(
        id=UUID('b0000000-0000-0000-0000-000000000001'),
        title='Задача',
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.IN_PROGRESS
    )
    db_session.add(task)
    await db_session.commit()

    response = await client.get(f'/api/v1/tasks/{task.id}')
    assert response.status_code == 200
    data = response.json()
    assert data['title'] == 'Задача'
    assert data['id'] == str(task.id)

    response = await client.get(
        '/api/v1/tasks/c0000000-0000-0000-0000-000000000001'
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_task(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_rabbitmq_producer: AsyncMock
):
    task_pending = Task(
        id=UUID('d0000000-0000-0000-0000-000000000001'),
        title='Задача 1',
        priority=TaskPriority.LOW,
        status=TaskStatus.PENDING
    )
    task_in_progress = Task(
        id=UUID('e0000000-0000-0000-0000-000000000001'),
        title='Задача 2',
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.IN_PROGRESS
    )
    db_session.add_all([task_pending, task_in_progress])
    await db_session.commit()

    response = await client.delete(f'/api/v1/tasks/{task_pending.id}')
    assert response.status_code == 204
    result = await db_session.execute(select(Task).where(Task.id == task_pending.id))
    task_pending = result.scalar_one()
    assert task_pending.status == TaskStatus.CANCELLED

    response = await client.delete(f'/api/v1/tasks/{task_in_progress.id}')
    assert response.status_code == 400
    assert 'in progress' in response.json()['detail']

    response = await client.delete(
        '/api/v1/tasks/f0000000-0000-0000-0000-000000000001'
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_task_status(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_rabbitmq_producer: AsyncMock
):
    task = Task(
        id=UUID('g0000000-0000-0000-0000-000000000001'),
        title='Задача',
        priority=TaskPriority.HIGH,
        status=TaskStatus.COMPLETED
    )
    db_session.add(task)
    await db_session.commit()

    response = await client.get(f'/api/v1/tasks/{task.id}/status')
    assert response.status_code == 200
    data = response.json()
    assert data['id'] == str(task.id)
    assert data['status'] == TaskStatus.COMPLETED.value

    response = await client.get(
        '/api/v1/tasks/h0000000-0000-0000-0000-000000000001/status'
    )
    assert response.status_code == 404
