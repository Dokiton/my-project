import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import engine
from app.core.security import get_password_hash
from app.main import app
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
def teacher_user(db_session: Session) -> User:
    user = User(
        email=f"teacher_course_{uuid.uuid4().hex[:8]}@edu.kz",
        full_name="Course Teacher",
        role="teacher",
        hashed_password=get_password_hash("TeacherPass123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_teacher(db_session: Session) -> User:
    user = User(
        email=f"other_teacher_{uuid.uuid4().hex[:8]}@edu.kz",
        full_name="Other Teacher",
        role="teacher",
        hashed_password=get_password_hash("TeacherPass123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def student_user(db_session: Session) -> User:
    user = User(
        email=f"student_course_{uuid.uuid4().hex[:8]}@edu.kz",
        full_name="Course Student",
        role="student",
        hashed_password=get_password_hash("StudentPass123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ==============================================================================
# 1. ЖЕКЕ ПРОФИЛЬ ЖӘНЕ ҚҰПИЯСӨЗ АУЫСТЫРУ (Users Me)
# ==============================================================================


def test_get_my_profile_unauthorized() -> None:
    res = client.get("/api/users/me")
    assert res.status_code == 401


def test_get_my_profile_success(student_user: User) -> None:
    res = client.get("/api/users/me", headers={"X-User-Id": str(student_user.id)})
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(student_user.id)
    assert data["email"] == student_user.email
    assert data["role"] == "student"


def test_change_password_lifecycle(student_user: User) -> None:
    # 1. Ескі құпиясөз қате болса -> 400
    res_fail = client.patch(
        "/api/users/me/password",
        json={"current_password": "WrongPassword123", "new_password": "NewSecretPassword123"},
        headers={"X-User-Id": str(student_user.id)},
    )
    assert res_fail.status_code == 400
    assert "Ескі құпиясөз қате" in res_fail.json()["detail"]

    # 2. Жаңа құпиясөз қысқа болса -> 422
    res_short = client.patch(
        "/api/users/me/password",
        json={"current_password": "StudentPass123", "new_password": "123"},
        headers={"X-User-Id": str(student_user.id)},
    )
    assert res_short.status_code == 422

    # 3. Дұрыс ауыстыру -> 200
    res_ok = client.patch(
        "/api/users/me/password",
        json={"current_password": "StudentPass123", "new_password": "NewSecretPassword123"},
        headers={"X-User-Id": str(student_user.id)},
    )
    assert res_ok.status_code == 200

    # 4. Жаңа құпиясөзбен логин жасап тексеру
    login_res = client.post(
        "/api/auth/login",
        json={"email": student_user.email, "password": "NewSecretPassword123"},
    )
    assert login_res.status_code == 200


# ==============================================================================
# 2. КУРСТАР ЖӘНЕ ОҚУҒА ЖАЗЫЛУ (Courses & Enrollments)
# ==============================================================================


def test_course_creation_and_listing(teacher_user: User, student_user: User) -> None:
    # 1. Студент курс аша алмайды -> 403
    fail_create = client.post(
        "/api/courses",
        json={"title": "Студенттің курсы", "description": "Рұқсатсыз"},
        headers={"X-User-Id": str(student_user.id)},
    )
    assert fail_create.status_code == 403

    # 2. Оқытушы курс ашады -> 201
    create_res = client.post(
        "/api/courses",
        json={"title": "Python Developer Pro", "description": "Нөлден бастап үйрену"},
        headers={"X-User-Id": str(teacher_user.id)},
    )
    assert create_res.status_code == 201
    course_data = create_res.json()
    assert course_data["title"] == "Python Developer Pro"
    assert course_data["teacher_id"] == str(teacher_user.id)
    course_id = course_data["id"]

    # 3. Барлық курстар тізімі -> 200
    list_res = client.get("/api/courses")
    assert list_res.status_code == 200
    assert any(c["id"] == course_id for c in list_res.json())

    # 4. Курс ID бойынша мәлімет -> 200
    get_res = client.get(f"/api/courses/{course_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == course_id


def test_course_enrollment_lifecycle(
    teacher_user: User, other_teacher: User, student_user: User
) -> None:
    # 1. Курс құру
    cr = client.post(
        "/api/courses",
        json={"title": "Алгоритмдер және деректер құрылымы", "description": "Күрделі курс"},
        headers={"X-User-Id": str(teacher_user.id)},
    )
    assert cr.status_code == 201
    course_id = cr.json()["id"]

    # 2. Оқытушы курсқа студент ретінде жазыла алмайды -> 403
    fail_teacher_enroll = client.post(
        f"/api/courses/{course_id}/enroll",
        headers={"X-User-Id": str(other_teacher.id)},
    )
    assert fail_teacher_enroll.status_code == 403

    # 3. Студент курсқа жазылады -> 201
    enroll_res = client.post(
        f"/api/courses/{course_id}/enroll",
        headers={"X-User-Id": str(student_user.id)},
    )
    assert enroll_res.status_code == 201
    assert enroll_res.json()["course_id"] == course_id
    assert enroll_res.json()["student_id"] == str(student_user.id)

    # 4. Қайта жазылуға тыйым -> 400
    duplicate_enroll = client.post(
        f"/api/courses/{course_id}/enroll",
        headers={"X-User-Id": str(student_user.id)},
    )
    assert duplicate_enroll.status_code == 400
    assert "бұрыннан жазылғансыз" in duplicate_enroll.json()["detail"]

    # 5. Студент өзінің жазылған курстарын көреді (GET /api/courses/my)
    my_courses_res = client.get(
        "/api/courses/my",
        headers={"X-User-Id": str(student_user.id)},
    )
    assert my_courses_res.status_code == 200
    assert any(c["id"] == course_id for c in my_courses_res.json())

    # 6. Оқытушы өз курсындағы студенттер тізімін көреді
    students_res = client.get(
        f"/api/courses/{course_id}/students",
        headers={"X-User-Id": str(teacher_user.id)},
    )
    assert students_res.status_code == 200
    students_list = students_res.json()
    assert len(students_list) >= 1
    assert any(s["student_id"] == str(student_user.id) for s in students_list)

    # 7. Басқа оқытушы бұл тізімді көре алмайды -> 403
    forbidden_students_res = client.get(
        f"/api/courses/{course_id}/students",
        headers={"X-User-Id": str(other_teacher.id)},
    )
    assert forbidden_students_res.status_code == 403
