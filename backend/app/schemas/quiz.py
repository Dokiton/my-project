from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.question import QuestionReadStudent, QuestionReadTeacher


class QuizCreate(BaseModel):
    """Схема создания теста."""

    title: str = Field(..., min_length=1, max_length=200, description="Тест атауы")
    description: str | None = Field(default=None, description="Тест сипаттамасы")


class QuizUpdate(BaseModel):
    """Схема обновления теста."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class QuizRead(BaseModel):
    """Схема чтения теста."""

    id: UUID
    title: str
    description: str | None
    is_published: bool
    author_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuizDetailStudent(QuizRead):
    """Студентке арналған тест мәліметі (сұрақтарында дұрыс жауап жоқ)."""

    questions: list[QuestionReadStudent] = []


class QuizDetailTeacher(QuizRead):
    """Оқытушыға/админге арналған тест мәліметі (дұрыс жауаптарымен)."""

    questions: list[QuestionReadTeacher] = []
