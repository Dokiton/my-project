from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import Identity
from app.models.user import User


class UserRepository:
    """Пайдаланушылар репозиторийі (тек SQLAlchemy)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self.db.scalars(statement).first()

    def get_by_keycloak_id(self, keycloak_id: str) -> User | None:
        statement = select(User).where(User.keycloak_id == keycloak_id)
        return self.db.scalars(statement).first()

    def get_by_id(self, id: UUID) -> User | None:
        return self.db.get(User, id)

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def sync(self, identity: Identity, role: str) -> User:
        """Keycloak пайдаланушысын жергілікті ДҚ-мен синхрондау."""
        user = self.get_by_keycloak_id(identity.keycloak_id)

        # Миграциядан қалған legacy- жазбасын email бойынша бір рет байланыстыру
        if user is None and identity.email:
            legacy = self.get_by_email(identity.email)
            if legacy and legacy.keycloak_id.startswith("legacy-"):
                user = legacy
                user.keycloak_id = identity.keycloak_id

        if user is None:
            email = identity.email or f"{identity.keycloak_id}@keycloak.local"
            full_name = identity.full_name or email
            return self.create(
                User(
                    keycloak_id=identity.keycloak_id,
                    email=email,
                    full_name=full_name,
                    role=role,
                )
            )

        target_email = identity.email or user.email
        target_name = identity.full_name or user.full_name
        if (
            user.email == target_email
            and user.full_name == target_name
            and user.role == role
            and not self.db.is_modified(user)
        ):
            return user

        user.email = target_email
        user.full_name = target_name
        user.role = role
        self.db.commit()
        self.db.refresh(user)
        return user
