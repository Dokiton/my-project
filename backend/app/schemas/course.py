from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CourseCreate(BaseModel):
    """Схема для создания курса (клиент жіберетін өрістер).

    id, teacher_id (иесі) және күй өрістері клиенттен қабылданбайды.
    """

    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Курс атауы (3-200 таңба)",
    )
    description: str | None = Field(
        default=None,
        description="Курс сипаттамасы",
    )


class CourseUpdate(BaseModel):
    """Схема для обновления курса (барлық өрістер міндетті емес)."""

    title: str | None = Field(
        default=None,
        min_length=3,
        max_length=200,
        description="Курс атауы (3-200 таңба)",
    )
    description: str | None = Field(
        default=None,
        description="Курс сипаттамасы",
    )


class CourseRead(BaseModel):
    """Схема для чтения курса."""

    id: UUID
    title: str
    description: str | None
    teacher_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
