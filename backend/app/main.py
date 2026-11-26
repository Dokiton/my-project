from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.database import engine
from app.routers.assignments import router as assignments_router
from app.routers.attempts import router as attempts_router
from app.routers.auth import router as auth_router
from app.routers.courses import router as courses_router
from app.routers.health import router as health_router
from app.routers.questions import router as questions_router
from app.routers.quizzes import router as quizzes_router
from app.routers.submissions import router as submissions_router
from app.routers.users import router as users_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    engine.dispose()


app = FastAPI(
    title=settings.app_name,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    swagger_ui_init_oauth={
        "clientId": settings.KEYCLOAK_CLIENT_ID,
        "usePkceWithAuthorizationCodeGrant": True,
        "scopes": "openid",
    },
    lifespan=lifespan,
)

# Негізгі сервистік роутер
app.include_router(health_router)

# Модуль 1–2: Аутентификация (/api/auth/me)
app.include_router(auth_router, prefix="/api")

# Модуль 3: Пайдаланушыларды басқару және жеке кабинет (/api/users)
app.include_router(users_router)

# Курстар және оқуға жазылу (/api/courses)
app.include_router(courses_router)

# Модуль 4–6: Тесттер, Сұрақтар, Жариялау және Тапсыру
app.include_router(quizzes_router)
app.include_router(questions_router)
app.include_router(attempts_router)

# Тапсырмалар мен жұмыстарды бағалау (Assignments & Submissions)
app.include_router(assignments_router)
app.include_router(submissions_router)
