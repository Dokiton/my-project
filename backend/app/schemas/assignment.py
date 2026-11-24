from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssignmentCreate(BaseModel):
    """Схема создания задания / теста."""

    title: str = Field(..., min_length=3, max_length=200, description="Тапсырма атауы (3-200 таңба)")
    description: str | None = Field(default=None, description="Тапсырма сипаттамасы")
    deadline: datetime | None = Field(default=None, description="Тапсыру мерзімі")
    course_id: UUID = Field(..., description="Қай курсқа тиесілі екендігі")


class AssignmentUpdate(BaseModel):
    """Схема обновления задания / теста."""

    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None
    deadline: datetime | None = None


class AssignmentRead(BaseModel):
    """Схема чтения задания / теста."""

    id: UUID
    title: str
    description: str | None
    deadline: datetime | None
    course_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
