from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assignment import Assignment


class AssignmentRepository:
    """Тапсырмалар репозиторийі (тек SQLAlchemy)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self, course_id: UUID | None = None, offset: int = 0, limit: int = 100
    ) -> Sequence[Assignment]:
        statement = select(Assignment)
        if course_id is not None:
            statement = statement.where(Assignment.course_id == course_id)
        statement = statement.offset(offset).limit(limit)
        return self.db.scalars(statement).all()

    def get(self, id: UUID) -> Assignment | None:
        return self.db.get(Assignment, id)

    def create(self, assignment: Assignment) -> Assignment:
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def save(self, assignment: Assignment) -> Assignment:
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def delete(self, assignment: Assignment) -> None:
        self.db.delete(assignment)
        self.db.commit()
