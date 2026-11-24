from collections.abc import Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.course import Course
from app.models.user import User
from app.repositories.assignment_repository import AssignmentRepository
from app.schemas.assignment import AssignmentCreate


class AssignmentService:
    """Тапсырмалар/тесттер басқарудың сервис қабаты."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AssignmentRepository(db)

    def create_assignment(
        self, assignment_in: AssignmentCreate, current_user: User
    ) -> Assignment:
        course = self.db.get(Course, assignment_in.course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Берілген ID бойынша курс табылмады",
            )

        # US-2.3: Оқытушы тек өзінің курсына ғана тапсырма қоса алады
        if course.teacher_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Сіз тек өзіңіз жүргізетін курсқа ғана тапсырма қоса аласыз",
            )

        assignment = Assignment(
            title=assignment_in.title,
            description=assignment_in.description,
            deadline=assignment_in.deadline,
            course_id=assignment_in.course_id,
        )
        return self.repo.create(assignment)

    def list_assignments(
        self, course_id: UUID | None = None, offset: int = 0, limit: int = 100
    ) -> Sequence[Assignment]:
        return self.repo.list(course_id=course_id, offset=offset, limit=limit)

    def get_assignment(self, id: UUID) -> Assignment:
        assignment = self.repo.get(id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тапсырма табылмады",
            )
        return assignment
