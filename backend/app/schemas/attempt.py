from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QuizAttemptCreate(BaseModel):
    """Схема сдачи теста."""

    answers: list[int] = Field(..., description="Жауаптардың индекстер тізімі")


class QuizAttemptRead(BaseModel):
    """Схема результата сдачи теста."""

    id: UUID
    quiz_id: UUID
    user_id: UUID
    answers: list[int]
    score: int
    total_questions: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
