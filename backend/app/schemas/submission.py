from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SubmissionCreate(BaseModel):
    """Тапсырма шешімін жіберу схемасы."""

    assignment_id: UUID = Field(..., description="Тапсырма ID")
    student_id: UUID = Field(..., description="Студент ID")
    code: str = Field(..., min_length=1, description="Жіберілген шешім коды немесе жауап")
    file_name: str | None = Field(default=None, max_length=255, description="Файл атауы")


class SubmissionGradeUpdate(BaseModel):
    """Студент жұмысын бағалау схемасы."""

    grade: int = Field(..., ge=0, le=100, description="Бағалау балы (0-100)")
    feedback: str | None = Field(default=None, description="Оқытушының пікірі / кері байланысы")


class SubmissionRead(BaseModel):
    """Жұмыс шешімін оқу схемасы."""

    id: UUID
    assignment_id: UUID
    student_id: UUID
    code: str
    file_name: str | None
    status: str
    grade: int | None
    feedback: str | None
    submitted_at: datetime
    graded_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class StudentSubmissionResult(BaseModel):
    """Студенттің тапсырма бойынша қорытынды нәтижесі."""

    submission_id: UUID
    student_id: UUID
    student_name: str
    student_email: str
    status: str
    grade: int | None
    feedback: str | None
    submitted_at: datetime
    graded_at: datetime | None


class AssignmentResultsSummary(BaseModel):
    """Тапсырма бойынша барлық пайдаланушылардың қорытынды статистикасы."""

    assignment_id: UUID
    assignment_title: str
    total_submissions: int
    graded_submissions: int
    average_grade: float | None
    results: list[StudentSubmissionResult]
