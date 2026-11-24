from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.user import User
from app.schemas.assignment import AssignmentCreate, AssignmentRead
from app.schemas.submission import AssignmentResultsSummary
from app.services.assignment_service import AssignmentService
from app.services.submission_service import SubmissionService

router = APIRouter(prefix="/api/v1/assignments", tags=["assignments"])


@router.post(
    "",
    response_model=AssignmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Жаңа тапсырма / тест құру (тек оқытушы немесе админ)",
)
def create_assignment(
    assignment_in: AssignmentCreate,
    current_user: User = Depends(require_roles("teacher", "admin")),
    db: Session = Depends(get_db),
) -> AssignmentRead:
    service = AssignmentService(db)
    assignment = service.create_assignment(assignment_in, current_user=current_user)
    return AssignmentRead.model_validate(assignment)


@router.get(
    "",
    response_model=list[AssignmentRead],
    summary="Тапсырмалар тізімін алу",
)
def list_assignments(
    course_id: UUID | None = Query(default=None, description="Курс ID фильтрі"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[AssignmentRead]:
    service = AssignmentService(db)
    assignments = service.list_assignments(
        course_id=course_id, offset=offset, limit=limit
    )
    return [AssignmentRead.model_validate(a) for a in assignments]


@router.get(
    "/{id}",
    response_model=AssignmentRead,
    summary="Нақты бір тапсырманың мәліметін алу",
)
def get_assignment(id: UUID, db: Session = Depends(get_db)) -> AssignmentRead:
    service = AssignmentService(db)
    assignment = service.get_assignment(id)
    return AssignmentRead.model_validate(assignment)


@router.get(
    "/{id}/results",
    response_model=AssignmentResultsSummary,
    summary="Тапсырма бойынша барлық пайдаланушылардың қорытынды нәтижелері",
)
def get_assignment_results(
    id: UUID, db: Session = Depends(get_db)
) -> AssignmentResultsSummary:
    service = SubmissionService(db)
    return service.get_assignment_results(id)
