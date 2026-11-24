from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course import Course


class CourseRepository:
    """Course репозиторийі — тек SQLAlchemy амалдары (бизнес-ереже мен HTTPException жоқ)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, offset: int = 0, limit: int = 100) -> Sequence[Course]:
        """Курстар тізімін алу."""
        statement = select(Course).offset(offset).limit(limit)
        return self.db.scalars(statement).all()

    def get(self, id: UUID) -> Course | None:
        """ID бойынша курсты табу."""
        return self.db.get(Course, id)

    def create(self, course: Course) -> Course:
        """Жаңа курс жазбасын қосу және сақтау."""
        self.db.add(course)
        self.db.commit()
        self.db.refresh(course)
        return course

    def save(self, course: Course) -> Course:
        """Өзгертілген курсты сақтау."""
        self.db.add(course)
        self.db.commit()
        self.db.refresh(course)
        return course

    def delete(self, course: Course) -> None:
        """Курс жазбасын өшіру."""
        self.db.delete(course)
        self.db.commit()
