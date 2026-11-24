from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.submission import Submission


class SubmissionRepository:
    """Тапсырма шешімдері репозиторийі (тек SQLAlchemy)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, id: UUID) -> Submission | None:
        return self.db.get(Submission, id)

    def list_by_assignment(self, assignment_id: UUID) -> Sequence[Submission]:
        statement = (
            select(Submission)
            .options(joinedload(Submission.student))
            .where(Submission.assignment_id == assignment_id)
            .order_by(Submission.submitted_at.desc())
        )
        return self.db.scalars(statement).all()

    def list_by_student(self, student_id: UUID) -> Sequence[Submission]:
        statement = (
            select(Submission)
            .where(Submission.student_id == student_id)
            .order_by(Submission.submitted_at.desc())
        )
        return self.db.scalars(statement).all()

    def create(self, submission: Submission) -> Submission:
        self.db.add(submission)
        self.db.commit()
        self.db.refresh(submission)
        return submission

    def save(self, submission: Submission) -> Submission:
        self.db.add(submission)
        self.db.commit()
        self.db.refresh(submission)
        return submission
