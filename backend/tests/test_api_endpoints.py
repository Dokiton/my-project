import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import engine
from app.main import app
from app.models.course import Course
from app.models.user import User

client = TestClient(app)
SessionTest = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture
def db_session():
    session = SessionTest()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def teacher(db_session: Session) -> User:
    user = User(
        keycloak_id=f"kc-{uuid.uuid4().hex[:12]}",
        email=f"teacher_{uuid.uuid4().hex[:8]}@edu.kz",
        full_name="Prof. John Doe",
        role="teacher",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def student(db_session: Session) -> User:
    user = User(
        keycloak_id=f"kc-{uuid.uuid4().hex[:12]}",
        email=f"student_{uuid.uuid4().hex[:8]}@edu.kz",
        full_name="Студент Қанат",
        role="student",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def teacher_auth_headers(teacher: User, auth_headers) -> dict[str, str]:
    return auth_headers(teacher)


@pytest.fixture
def student_auth_headers(student: User, auth_headers) -> dict[str, str]:
    return auth_headers(student)


@pytest.fixture
def course(db_session: Session, teacher: User) -> Course:
    c = Course(
        title="Computer Science 101",
        description="Intro to algorithms",
        teacher_id=teacher.id,
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


# =======================================================
# 1. ТАПСЫРМА / ТЕСТ ҚҰРУ API-ІН ТЕСТІЛЕУ (Assignments)
# =======================================================


def test_create_assignment_success(
    course: Course, teacher_auth_headers: dict[str, str]
) -> None:
    payload = {
        "title": "1-зертханалық жұмыс: Циклдар",
        "description": "Python тілінде for және while циклдерін пайдалану",
        "deadline": datetime.now(timezone.utc).isoformat(),
        "course_id": str(course.id),
    }
    response = client.post(
        "/api/v1/assignments", json=payload, headers=teacher_auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["course_id"] == str(course.id)
    assert "id" in data


def test_create_assignment_unauthorized_without_token(course: Course) -> None:
    payload = {
        "title": "Токенсіз тапсырма",
        "course_id": str(course.id),
    }
    response = client.post("/api/v1/assignments", json=payload)
    assert response.status_code == 401
    assert "Bearer" in response.json()["detail"]


def test_create_assignment_forbidden_for_student(
    course: Course, student_auth_headers: dict[str, str]
) -> None:
    payload = {
        "title": "Студент құрған тапсырма",
        "course_id": str(course.id),
    }
    response = client.post(
        "/api/v1/assignments", json=payload, headers=student_auth_headers
    )
    assert response.status_code == 403
    detail = response.json()["detail"]
    assert "рөл" in detail.lower() or "құқығыңыз жоқ" in detail


def test_create_assignment_forbidden_for_other_teacher(
    course: Course, db_session: Session, auth_headers
) -> None:
    other_teacher = User(
        keycloak_id=f"kc-{uuid.uuid4().hex[:12]}",
        email=f"other_{uuid.uuid4().hex[:8]}@edu.kz",
        full_name="Other Teacher",
        role="teacher",
    )
    db_session.add(other_teacher)
    db_session.commit()
    db_session.refresh(other_teacher)

    headers = auth_headers(other_teacher)

    payload = {
        "title": "Басқа мұғалімнің тапсырмасы",
        "course_id": str(course.id),
    }
    response = client.post("/api/v1/assignments", json=payload, headers=headers)
    assert response.status_code == 403
    assert "өзіңіз жүргізетін курсқа" in response.json()["detail"]


def test_create_assignment_course_not_found(
    teacher_auth_headers: dict[str, str],
) -> None:
    fake_course_id = str(uuid.uuid4())
    payload = {
        "title": "Тапсырма",
        "description": "Сипаттама",
        "course_id": fake_course_id,
    }
    response = client.post(
        "/api/v1/assignments", json=payload, headers=teacher_auth_headers
    )
    assert response.status_code == 404
    assert "курс табылмады" in response.json()["detail"]


def test_create_assignment_validation_error(
    teacher_auth_headers: dict[str, str],
) -> None:
    payload = {
        "title": "AB",  # < 3 таңба
        "course_id": str(uuid.uuid4()),
    }
    response = client.post(
        "/api/v1/assignments", json=payload, headers=teacher_auth_headers
    )
    assert response.status_code == 422


def test_list_and_get_assignments(
    course: Course, teacher_auth_headers: dict[str, str]
) -> None:
    payload = {
        "title": "Тесттік тапсырма 1",
        "description": "Мәліметтер құрылымы",
        "course_id": str(course.id),
    }
    create_resp = client.post(
        "/api/v1/assignments", json=payload, headers=teacher_auth_headers
    )
    assert create_resp.status_code == 201
    assignment_id = create_resp.json()["id"]

    list_resp = client.get(f"/api/v1/assignments?course_id={course.id}")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(item["id"] == assignment_id for item in items)

    get_resp = client.get(f"/api/v1/assignments/{assignment_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == assignment_id
    assert get_resp.json()["title"] == "Тесттік тапсырма 1"


def test_get_assignment_not_found() -> None:
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/assignments/{fake_id}")
    assert response.status_code == 404


# ==============================================================================
# 2. ТАПСЫРМАЛАРДЫ ТАПСЫРУ, БАҒАЛАУ ЖӘНЕ ҚОРЫТЫНДЫЛАР API (Submissions & Results)
# ==============================================================================


def test_submission_lifecycle_and_assignment_results(
    course: Course, student: User, teacher_auth_headers: dict[str, str]
) -> None:
    assign_resp = client.post(
        "/api/v1/assignments",
        json={
            "title": "SQL қорытынды тесті",
            "description": "SELECT және JOIN сұраныстарын жазу",
            "course_id": str(course.id),
        },
        headers=teacher_auth_headers,
    )
    assert assign_resp.status_code == 201
    assignment_id = assign_resp.json()["id"]

    sub_payload = {
        "assignment_id": assignment_id,
        "student_id": str(student.id),
        "code": "SELECT * FROM users JOIN courses ON users.id = courses.teacher_id;",
        "file_name": "solution.sql",
    }
    sub_resp = client.post("/api/v1/submissions", json=sub_payload)
    assert sub_resp.status_code == 201
    sub_data = sub_resp.json()
    submission_id = sub_data["id"]
    assert sub_data["status"] == "submitted"
    assert sub_data["grade"] is None

    grade_payload = {
        "grade": 95,
        "feedback": "Жарайсың! Сұраныс оңтайлы орындалған.",
    }
    grade_resp = client.patch(
        f"/api/v1/submissions/{submission_id}/grade",
        json=grade_payload,
    )
    assert grade_resp.status_code == 200
    graded_data = grade_resp.json()
    assert graded_data["status"] == "graded"
    assert graded_data["grade"] == 95
    assert graded_data["feedback"] == grade_payload["feedback"]
    assert graded_data["graded_at"] is not None

    get_sub_resp = client.get(f"/api/v1/submissions/{submission_id}")
    assert get_sub_resp.status_code == 200
    assert get_sub_resp.json()["grade"] == 95

    results_resp = client.get(f"/api/v1/assignments/{assignment_id}/results")
    assert results_resp.status_code == 200
    results_data = results_resp.json()
    assert results_data["assignment_id"] == assignment_id
    assert results_data["total_submissions"] == 1
    assert results_data["graded_submissions"] == 1
    assert results_data["average_grade"] == 95.0
    assert len(results_data["results"]) == 1
    student_res = results_data["results"][0]
    assert student_res["student_id"] == str(student.id)
    assert student_res["student_name"] == student.full_name
    assert student_res["grade"] == 95


def test_grade_submission_invalid_score() -> None:
    fake_sub_id = str(uuid.uuid4())
    resp = client.patch(
        f"/api/v1/submissions/{fake_sub_id}/grade",
        json={"grade": 150},
    )
    assert resp.status_code == 422
