from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import LoginResponse, UserLogin, UserRegister


class UserService:
    """Пайдаланушыларды тіркеу және басқару бизнес-логикасы."""

    def __init__(self, db: Session) -> None:
        self.repo = UserRepository(db)

    def register(self, user_in: UserRegister) -> User:
        existing = self.repo.get_by_email(user_in.email)
        if existing:
            # Спецификация бойынша: егер email бар болса -> 409 Conflict
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Бұл email-мен пайдаланушы бұрыннан тіркелген",
            )

        user = User(
            email=user_in.email,
            full_name=user_in.full_name,
            role=user_in.role,
            hashed_password=get_password_hash(user_in.password),
        )
        return self.repo.create(user)

    def login(self, login_in: UserLogin) -> LoginResponse:
        user = self.repo.get_by_email(login_in.email)
        if not user or not verify_password(login_in.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email немесе құпиясөз қате",
            )
        # Спецификация: Токен не выдаётся, это только проверка -> 200 OK
        return LoginResponse(status="ok")
