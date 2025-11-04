from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Text, UUID, Index
from sqlalchemy.dialects.postgresql import ENUM

from enum import Enum
from datetime import datetime

import uuid

from app.db.base import Base


class TaskPriority(str, Enum):
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'


class TaskStatus(str, Enum):
    NEW = 'NEW'
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'


class Task(Base):
    __tablename__ = 'tasks'
    __table_args__ = (Index('ix_tasks_status_priority', 'status', 'priority'),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    priority: Mapped[TaskPriority] = mapped_column(
        ENUM(TaskPriority, name='task_priority', create_type=True),
        default=TaskPriority.MEDIUM,
        nullable=False
    )
    status: Mapped[TaskStatus] = mapped_column(
        ENUM(TaskStatus, name='task_status', create_type=True),
        default=TaskStatus.NEW,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    result: Mapped[str] = mapped_column(Text, nullable=True)
    error_info: Mapped[str] = mapped_column(Text, nullable=True)
