from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionGradeUpdate,
    SubmissionRead,
)
from app.services.submission_service import SubmissionService

router = APIRouter(prefix="/api/v1/submissions", tags=["submissions"])


@router.post(
    "",
    response_model=SubmissionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Тапсырма шешімін тапсыру",
)
def submit_assignment(
    data: SubmissionCreate, db: Session = Depends(get_db)
) -> SubmissionRead:
    service = SubmissionService(db)
    sub = service.submit(data)
    return SubmissionRead.model_validate(sub)


@router.patch(
    "/{id}/grade",
    response_model=SubmissionRead,
    summary="Студент жұмысын бағалау және пікір қалдыру",
)
def grade_submission(
    id: UUID, data: SubmissionGradeUpdate, db: Session = Depends(get_db)
) -> SubmissionRead:
    service = SubmissionService(db)
    sub = service.grade(id, data)
    return SubmissionRead.model_validate(sub)


@router.get(
    "/{id}",
    response_model=SubmissionRead,
    summary="Жіберілген жұмыстың нәтижесі мен бағасын көру",
)
def get_submission(id: UUID, db: Session = Depends(get_db)) -> SubmissionRead:
    service = SubmissionService(db)
    sub = service.get(id)
    return SubmissionRead.model_validate(sub)
