import uuid
from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Пайдаланушыны X-User-Id немесе Bearer токен арқылы анықтау."""
    # 1. Тікелей X-User-Id тақырыбы арқылы тексеру (тесттер мен клиенттер үшін)
    if x_user_id:
        try:
            uid = uuid.UUID(x_user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Жарамсыз X-User-Id",
            )
        user = db.get(User, uid)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пайдаланушы табылмады",
            )
        return user

    # 2. Bearer токен арқылы тексеру
    if credentials:
        payload = decode_access_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Токен жарамсыз немесе мерзімі өткен",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Токенде пайдаланушы мәліметі табылмады",
            )
        try:
            uid = uuid.UUID(user_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Жарамсыз пайдаланушы идентификаторы",
            )
        user = db.get(User, uid)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Пайдаланушы табылмады",
            )
        return user

    # 3. Екеуі де жоқ болса
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Авторизация қажет (X-User-Id немесе Bearer токен)",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_roles(*roles: str) -> Callable[[User], User]:
    """Рөлдерді тексеру тәуелділігі (RBAC)."""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Бұл әрекетті орындауға құқығыңыз жоқ. Қажетті рөл: {', '.join(roles)}",
            )
        return current_user

    return role_checker
