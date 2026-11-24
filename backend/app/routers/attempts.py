from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.quiz_attempt import QuizAttempt
from app.models.user import User
from app.schemas.attempt import QuizAttemptRead

router = APIRouter(prefix="/api/attempts", tags=["attempts"])


@router.get("/me", response_model=list[QuizAttemptRead], summary="Студенттің өз әрекеттері (мои попытки)")
def get_my_attempts(
    current_user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
) -> list[QuizAttemptRead]:
    statement = (
        select(QuizAttempt)
        .where(QuizAttempt.user_id == current_user.id)
        .order_by(QuizAttempt.created_at.desc())
    )
    attempts = db.scalars(statement).all()
    return [QuizAttemptRead.model_validate(a) for a in attempts]
