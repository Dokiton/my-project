from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QuestionCreate(BaseModel):
    """Схема создания вопроса."""

    text: str = Field(..., min_length=1, description="Сұрақ мәтіні")
    options: list[str] = Field(..., min_length=2, description="Жауап нұсқалары")
    correct_index: int = Field(..., ge=0, description="Дұрыс нұсқаның индексі")


class QuestionUpdate(BaseModel):
    """Схема обновления вопроса."""

    text: str | None = None
    options: list[str] | None = None
    correct_index: int | None = None


class QuestionReadStudent(BaseModel):
    """Студентке арналған сұрақ схемасы (дұрыс жауапсыз)."""

    id: UUID
    quiz_id: UUID
    text: str
    options: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionReadTeacher(BaseModel):
    """Оқытушы мен админге арналған толық сұрақ схемасы."""

    id: UUID
    quiz_id: UUID
    text: str
    options: list[str]
    correct_index: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
