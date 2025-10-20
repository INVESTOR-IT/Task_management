from pydantic import BaseModel, Field

from datetime import datetime
from uuid import UUID

from app.models.task import TaskPriority, TaskStatus


class TaskBase(BaseModel):
    title: str = Field(..., max_length=255, description='Название задачи')
    description: str | None = Field(None, description='Описание задачи')
    priority: TaskPriority = Field(
        TaskPriority.MEDIUM,
        description='Приоритет задачи'
    )


class TaskCreate(TaskBase):
    pass


class TaskUpdateStatus(BaseModel):
    status: TaskStatus = Field(..., description='Новый статус задачи')


class TaskResponse(TaskBase):
    id: UUID
    status: TaskStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    result: str | None
    error_info: str | None

    class Config:
        from_attributes = True


class TaskStatusResponse(BaseModel):
    id: UUID
    status: TaskStatus

    class Config():
        from_attributes = True


class PaginatedTasksResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[TaskResponse]

    class Config:
        from_attributes = True
