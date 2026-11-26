from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserRead,
    summary="Ағымдағы пайдаланушының жеке профилі",
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    return UserRead.model_validate(current_user)


@router.get(
    "",
    response_model=list[UserRead],
    summary="Пайдаланушылар тізімі (тек admin)",
)
def list_users(
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> list[UserRead]:
    statement = select(User).order_by(User.created_at.asc())
    users = db.scalars(statement).all()
    return [UserRead.model_validate(u) for u in users]


@router.get(
    "/{id}",
    response_model=UserRead,
    summary="Пайдаланушы мәліметі (тек admin)",
)
def get_user(
    id: UUID,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> UserRead:
    user = db.get(User, id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пайдаланушы табылмады",
        )
    return UserRead.model_validate(user)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Пайдаланушыны жою (тек admin)",
)
def delete_user(
    id: UUID,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> None:
    target_user = db.get(User, id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пайдаланушы табылмады",
        )

    if current_user.id == target_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Өзіңізді өшіруге болмайды",
        )

    db.delete(target_user)
    db.commit()
