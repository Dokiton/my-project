import logging
from collections.abc import Callable
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    AuthUnavailableError,
    KeycloakVerifier,
    identity_from_claims,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{settings.keycloak_issuer}/protocol/openid-connect/auth",
    tokenUrl=f"{settings.keycloak_issuer}/protocol/openid-connect/token",
    scopes={"openid": "OpenID Connect"},
    auto_error=False,
)


@lru_cache(maxsize=1)
def get_keycloak_verifier() -> KeycloakVerifier:
    """Keycloak JWT тексерушісін кэшпен инициализациялау."""
    return KeycloakVerifier(
        issuer=settings.keycloak_issuer,
        jwks_url=settings.keycloak_jwks_url,
        audience=settings.KEYCLOAK_AUDIENCE,
    )


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    verifier: KeycloakVerifier = Depends(get_keycloak_verifier),
) -> User:
    """Пайдаланушыны Keycloak Bearer токені арқылы тексеріп анықтау."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Авторизация қажет (Bearer токен)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = verifier.verify(token)
        identity = identity_from_claims(claims)
    except AuthUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Keycloak қолжетімсіз",
        )
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        logger.warning("Токен қабылданбады: %s: %s", type(exc).__name__, exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен жоқ, қате немесе мерзімі өткен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if identity.role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Keycloak-та қосымша рөлі берілмеген",
        )

    return UserRepository(db).sync(identity, identity.role)


def require_roles(*roles: str) -> Callable[[User], User]:
    """Рөлдерді тексеру тәуелділігі (RBAC)."""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Бұл әрекетті орындауға құқығыңыз жоқ. "
                    f"Қажетті рөл: {', '.join(roles)}"
                ),
            )
        return current_user

    return role_checker
