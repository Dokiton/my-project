from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.user import User
from app.repositories.submission_repository import SubmissionRepository
from app.schemas.submission import (
    AssignmentResultsSummary,
    StudentSubmissionResult,
    SubmissionCreate,
    SubmissionGradeUpdate,
)


class SubmissionService:
    """Тапсырма шешімдері мен бағалау қорытындыларының сервис қабаты."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SubmissionRepository(db)

    def submit(self, data: SubmissionCreate) -> Submission:
        assignment = self.db.get(Assignment, data.assignment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тапсырма табылмады",
            )
        student = self.db.get(User, data.student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Студент табылмады",
            )
        submission = Submission(
            assignment_id=data.assignment_id,
            student_id=data.student_id,
            code=data.code,
            file_name=data.file_name,
            status="submitted",
        )
        return self.repo.create(submission)

    def grade(self, submission_id: UUID, data: SubmissionGradeUpdate) -> Submission:
        submission = self.repo.get(submission_id)
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Студент шешімі табылмады",
            )
        submission.grade = data.grade
        submission.feedback = data.feedback
        submission.status = "graded"
        submission.graded_at = datetime.now(timezone.utc)
        return self.repo.save(submission)

    def get(self, submission_id: UUID) -> Submission:
        submission = self.repo.get(submission_id)
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Студент шешімі табылмады",
            )
        return submission

    def get_assignment_results(self, assignment_id: UUID) -> AssignmentResultsSummary:
        assignment = self.db.get(Assignment, assignment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тапсырма табылмады",
            )
        submissions = self.repo.list_by_assignment(assignment_id)
        results: list[StudentSubmissionResult] = []
        graded_scores: list[int] = []
        for s in submissions:
            student_name = s.student.full_name if s.student else "Белгісіз"
            student_email = s.student.email if s.student else ""
            if s.grade is not None:
                graded_scores.append(s.grade)
            results.append(
                StudentSubmissionResult(
                    submission_id=s.id,
                    student_id=s.student_id,
                    student_name=student_name,
                    student_email=student_email,
                    status=s.status,
                    grade=s.grade,
                    feedback=s.feedback,
                    submitted_at=s.submitted_at,
                    graded_at=s.graded_at,
                )
            )

        avg_grade = (
            round(sum(graded_scores) / len(graded_scores), 2)
            if graded_scores
            else None
        )

        return AssignmentResultsSummary(
            assignment_id=assignment.id,
            assignment_title=assignment.title,
            total_submissions=len(submissions),
            graded_submissions=len(graded_scores),
            average_grade=avg_grade,
            results=results,
        )
