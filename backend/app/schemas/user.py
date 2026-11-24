from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserRegister(BaseModel):
    """Схема регистрации нового пользователя."""

    email: str = Field(
        ...,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="Электрондық пошта",
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="Құпиясөз (кемінде 6 таңба)",
    )
    full_name: str = Field(..., min_length=2, max_length=255, description="Аты-жөні")
    role: str = Field(default="student", description="Рөлі (student немесе teacher)")

    @field_validator("role")
    @classmethod
    def validate_role_not_admin(cls, value: str) -> str:
        if value == "admin":
            raise ValueError("role: admin тіркелу кезінде рұқсат етілмейді")
        if value not in ("student", "teacher"):
            raise ValueError("Рұқсат етілген рөлдер: student, teacher")
        return value


class UserLogin(BaseModel):
    """Схема входа пользователя."""

    email: str = Field(..., description="Электрондық пошта")
    password: str = Field(..., description="Құпиясөз")


class UserUpdate(BaseModel):
    """Схема обновления пользователя (имя и роль)."""

    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    role: str | None = Field(default=None)


class PasswordChangeRequest(BaseModel):
    """Схема смены пароля пользователя."""

    current_password: str = Field(..., description="Ағымдағы құпиясөз")
    new_password: str = Field(
        ..., min_length=6, max_length=128, description="Жаңа құпиясөз (кемінде 6 таңба)"
    )


class UserRead(BaseModel):
    """Схема чтения информации о пользователе."""

    id: UUID
    email: str
    full_name: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    """Схема ответа при логине (токен берілмейді, тек тексеру)."""

    status: str = "ok"
