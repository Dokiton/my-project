from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user import LoginResponse, UserLogin, UserRead, UserRegister
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Жаңа пайдаланушыны тіркеу",
)
def register(user_in: UserRegister, db: Session = Depends(get_db)) -> UserRead:
    service = UserService(db)
    user = service.register(user_in)
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Жүйеге кіруді тексеру (Логин)",
)
def login(login_in: UserLogin, db: Session = Depends(get_db)) -> LoginResponse:
    service = UserService(db)
    return service.login(login_in)
