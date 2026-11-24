from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EnrollmentRead(BaseModel):
    """Схема чтения записи о записи на курс."""

    id: UUID
    course_id: UUID
    student_id: UUID
    enrolled_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EnrolledStudentItem(BaseModel):
    """Схема данных о студенте, записанном на курс."""

    student_id: UUID
    student_name: str
    student_email: str
    enrolled_at: datetime
