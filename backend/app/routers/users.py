from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import PasswordChangeRequest, UserRead, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


# ==========================================
# Жеке профиль (Users Me)
# ==========================================


@router.get("/me", response_model=UserRead, summary="Ағымдағы пайдаланушының жеке профилі")
def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me/password", summary="Құпиясөзді ауыстыру")
def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ескі құпиясөз қате",
        )
    current_user.hashed_password = get_password_hash(data.new_password)
    db.add(current_user)
    db.commit()
    return {"status": "ok", "message": "Құпиясөз сәтті жаңартылды"}


# ==========================================
# Әкімшілік басқару (Admin Users)
# ==========================================


@router.get("", response_model=list[UserRead], summary="Пайдаланушылар тізімі (тек admin)")
def list_users(
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> list[UserRead]:
    statement = select(User).order_by(User.created_at.asc())
    users = db.scalars(statement).all()
    return [UserRead.model_validate(u) for u in users]


@router.get("/{id}", response_model=UserRead, summary="Пайдаланушы мәліметі (тек admin)")
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


@router.patch("/{id}", response_model=UserRead, summary="Пайдаланушыны жаңарту (тек admin)")
def update_user(
    id: UUID,
    user_in: UserUpdate,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> UserRead:
    target_user = db.get(User, id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пайдаланушы табылмады",
        )

    # Ереже: Свою роль менять нельзя -> 400 Bad Request
    if (
        current_user.id == target_user.id
        and user_in.role is not None
        and user_in.role != target_user.role
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Өз рөліңізді өзгертуге болмайды",
        )

    if user_in.full_name is not None:
        target_user.full_name = user_in.full_name
    if user_in.role is not None:
        if user_in.role not in ("student", "teacher", "admin"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Рұқсат етілген рөлдер: student, teacher, admin",
            )
        target_user.role = user_in.role

    db.add(target_user)
    db.commit()
    db.refresh(target_user)
    return UserRead.model_validate(target_user)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="Пайдаланушыны жою (тек admin)")
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

    # Ереже: Удалить себя нельзя -> 400 Bad Request
    if current_user.id == target_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Өзіңізді өшіруге болмайды",
        )

    db.delete(target_user)
    db.commit()
