import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import engine
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
def admin_user(db_session: Session) -> User:
    user = User(
        email=f"admin_{uuid.uuid4().hex[:8]}@edu.kz",
        full_name="Admin User",
        role="admin",
        hashed_password="dummy_hash",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def teacher_1(db_session: Session) -> User:
    user = User(
        email=f"teacher1_{uuid.uuid4().hex[:8]}@edu.kz",
        full_name="Teacher One",
        role="teacher",
        hashed_password="dummy_hash",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def teacher_2(db_session: Session) -> User:
    user = User(
        email=f"teacher2_{uuid.uuid4().hex[:8]}@edu.kz",
        full_name="Teacher Two",
        role="teacher",
        hashed_password="dummy_hash",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def student_1(db_session: Session) -> User:
    user = User(
        email=f"student1_{uuid.uuid4().hex[:8]}@edu.kz",
        full_name="Student One",
        role="student",
        hashed_password="dummy_hash",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ==============================================================================
# Служебный: GET /api/health
# ==============================================================================


def test_service_health() -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] in ("ok", "degraded")


# ==============================================================================
# Модуль 1–2: Регистрация и проверка входа
# ==============================================================================


def test_auth_register_success() -> None:
    email = f"user_{uuid.uuid4().hex[:8]}@edu.kz"
    res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "StrongPassword123", "full_name": "Test User", "role": "student"},
    )
    assert res.status_code == 201
    data = res.json()
    assert "password" not in data
    assert "hashed_password" not in data
    assert data["email"] == email


def test_auth_register_duplicate_email_409() -> None:
    email = f"dup_{uuid.uuid4().hex[:8]}@edu.kz"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "StrongPassword123", "full_name": "Test User", "role": "student"},
    )
    res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "StrongPassword123", "full_name": "Test User", "role": "student"},
    )
    assert res.status_code == 409


def test_auth_register_short_password_422() -> None:
    res = client.post(
        "/api/auth/register",
        json={"email": "short@edu.kz", "password": "123", "full_name": "Test User", "role": "student"},
    )
    assert res.status_code == 422


def test_auth_register_role_admin_422() -> None:
    res = client.post(
        "/api/auth/register",
        json={"email": "admin_attempt@edu.kz", "password": "StrongPassword123", "full_name": "Hacker", "role": "admin"},
    )
    assert res.status_code == 422


def test_auth_login_check() -> None:
    email = f"log_{uuid.uuid4().hex[:8]}@edu.kz"
    password = "CorrectPassword123"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Login User", "role": "student"},
    )
    # Сәтті кіру
    res_ok = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res_ok.status_code == 200
    assert "token" not in res_ok.json()

    # Қате құпиясөз
    res_fail = client.post("/api/auth/login", json={"email": email, "password": "WrongPassword"})
    assert res_fail.status_code == 401
    assert "Email немесе құпиясөз қате" in res_fail.json()["detail"]


# ==============================================================================
# Модуль 3: Управление пользователями (только admin)
# ==============================================================================


def test_users_list_admin_only(admin_user: User, teacher_1: User, student_1: User) -> None:
    # Admin көре алады -> 200
    res_admin = client.get("/api/users", headers={"X-User-Id": str(admin_user.id)})
    assert res_admin.status_code == 200
    assert isinstance(res_admin.json(), list)

    # Teacher -> 403
    res_teacher = client.get("/api/users", headers={"X-User-Id": str(teacher_1.id)})
    assert res_teacher.status_code == 403

    # Student -> 403
    res_student = client.get("/api/users", headers={"X-User-Id": str(student_1.id)})
    assert res_student.status_code == 403


def test_users_get_by_id(admin_user: User, student_1: User) -> None:
    res = client.get(f"/api/users/{student_1.id}", headers={"X-User-Id": str(admin_user.id)})
    assert res.status_code == 200
    assert res.json()["id"] == str(student_1.id)

    res_404 = client.get(f"/api/users/{uuid.uuid4()}", headers={"X-User-Id": str(admin_user.id)})
    assert res_404.status_code == 404


def test_users_patch_role_and_cannot_change_own_role(admin_user: User, student_1: User) -> None:
    # Басқа қолданушының рөлін және атын өзгерту -> 200
    res = client.patch(
        f"/api/users/{student_1.id}",
        json={"full_name": "New Student Name", "role": "teacher"},
        headers={"X-User-Id": str(admin_user.id)},
    )
    assert res.status_code == 200
    assert res.json()["full_name"] == "New Student Name"
    assert res.json()["role"] == "teacher"

    # Өз рөлін өзі өзгертуге тыйым -> 400
    res_self = client.patch(
        f"/api/users/{admin_user.id}",
        json={"role": "student"},
        headers={"X-User-Id": str(admin_user.id)},
    )
    assert res_self.status_code == 400


def test_users_delete_and_cannot_delete_self(admin_user: User, db_session: Session) -> None:
    temp_user = User(email="temp@edu.kz", full_name="Temp", role="student", hashed_password="x")
    db_session.add(temp_user)
    db_session.commit()
    db_session.refresh(temp_user)

    # Өзін өшіруге тыйым -> 400
    res_self = client.delete(f"/api/users/{admin_user.id}", headers={"X-User-Id": str(admin_user.id)})
    assert res_self.status_code == 400

    # Басқаны өшіру -> 204
    res_del = client.delete(f"/api/users/{temp_user.id}", headers={"X-User-Id": str(admin_user.id)})
    assert res_del.status_code == 204


# ==============================================================================
# Модуль 4 & 5 & 6: Тесттер (Quiz), Сұрақтар және Тапсыру
# ==============================================================================


def test_quiz_lifecycle_modules_4_5_6(
    admin_user: User, teacher_1: User, teacher_2: User, student_1: User
) -> None:
    # --- МОДУЛЬ 4: Тест құру ---
    # Студент тест құра алмайды -> 403
    fail_create = client.post(
        "/api/quizzes",
        json={"title": "Студент тесті"},
        headers={"X-User-Id": str(student_1.id)},
    )
    assert fail_create.status_code == 403

    # Teacher 1 тест құрады -> 201
    create_res = client.post(
        "/api/quizzes",
        json={"title": "Python негіздері", "description": "Сұрақ-жауап"},
        headers={"X-User-Id": str(teacher_1.id)},
    )
    assert create_res.status_code == 201
    quiz_id = create_res.json()["id"]

    # --- МОДУЛЬ 5: Сұрақ қосу ---
    # Бөтен оқытушы (Teacher 2) сұрақ қоса алмайды -> 403
    res_other_teacher_q = client.post(
        f"/api/quizzes/{quiz_id}/questions",
        json={"text": "2+2 неше?", "options": ["3", "4", "5"], "correct_index": 1},
        headers={"X-User-Id": str(teacher_2.id)},
    )
    assert res_other_teacher_q.status_code == 403

    # correct_index options шегінен тыс болса -> 400
    res_bad_idx = client.post(
        f"/api/quizzes/{quiz_id}/questions",
        json={"text": "Қате сұрақ", "options": ["А", "Б"], "correct_index": 5},
        headers={"X-User-Id": str(teacher_1.id)},
    )
    assert res_bad_idx.status_code == 400

    # Дұрыс сұрақтарды қосу -> 201
    q1_res = client.post(
        f"/api/quizzes/{quiz_id}/questions",
        json={"text": "Python-да тізім қалай жазылады?", "options": ["[]", "{}", "()"], "correct_index": 0},
        headers={"X-User-Id": str(teacher_1.id)},
    )
    assert q1_res.status_code == 201
    q1_id = q1_res.json()["id"]

    q2_res = client.post(
        f"/api/quizzes/{quiz_id}/questions",
        json={"text": "Сөздік қалай жазылады?", "options": ["[]", "{}", "()"], "correct_index": 1},
        headers={"X-User-Id": str(teacher_1.id)},
    )
    assert q2_res.status_code == 201
    q2_id = q2_res.json()["id"]

    # Сұрақты жаңарту (PATCH /api/questions/{id}) -> 200
    patch_q_res = client.patch(
        f"/api/questions/{q1_id}",
        json={"text": "Python-да жаңартылған тізім?"},
        headers={"X-User-Id": str(teacher_1.id)},
    )
    assert patch_q_res.status_code == 200

    # Бөтен оқытушы сұрақты өзгерте алмайды -> 403
    fail_patch_q = client.patch(
        f"/api/questions/{q1_id}",
        json={"text": "Хакер сұрағы"},
        headers={"X-User-Id": str(teacher_2.id)},
    )
    assert fail_patch_q.status_code == 403

    # --- МОДУЛЬ 6: Жариялау ---
    # Бөтен оқытушы жариялай алмайды -> 403
    fail_pub = client.post(
        f"/api/quizzes/{quiz_id}/publish",
        headers={"X-User-Id": str(teacher_2.id)},
    )
    assert fail_pub.status_code == 403

    # Жарияланғанға дейін студент бұл тестті көре алмайды
    res_list_student_before = client.get("/api/quizzes", headers={"X-User-Id": str(student_1.id)})
    assert not any(q["id"] == quiz_id for q in res_list_student_before.json())

    # Жариялау -> 200
    pub_res = client.post(
        f"/api/quizzes/{quiz_id}/publish",
        headers={"X-User-Id": str(teacher_1.id)},
    )
    assert pub_res.status_code == 200
    assert pub_res.json()["is_published"] is True

    # Жарияланған тестке жаңа сұрақ қосуға тыйым -> 400
    fail_add_after_pub = client.post(
        f"/api/quizzes/{quiz_id}/questions",
        json={"text": "Кеш қосылған", "options": ["А", "Б"], "correct_index": 0},
        headers={"X-User-Id": str(teacher_1.id)},
    )
    assert fail_add_after_pub.status_code == 400

    # Жарияланған тесттің сұрағын өзгертуге тыйым -> 400
    fail_edit_after_pub = client.patch(
        f"/api/questions/{q1_id}",
        json={"text": "Жарияланған соң өзгерту"},
        headers={"X-User-Id": str(teacher_1.id)},
    )
    assert fail_edit_after_pub.status_code == 400

    # --- МОДУЛЬ 4: Студент тестті қарайды (дұрыс жауапсыз!) ---
    student_view = client.get(f"/api/quizzes/{quiz_id}", headers={"X-User-Id": str(student_1.id)})
    assert student_view.status_code == 200
    q_data_student = student_view.json()["questions"][0]
    assert "correct_index" not in q_data_student  # Дұрыс жауап жоқ!

    # Оқытушы қарағанда дұрыс жауап бар
    teacher_view = client.get(f"/api/quizzes/{quiz_id}", headers={"X-User-Id": str(teacher_1.id)})
    assert teacher_view.status_code == 200
    assert "correct_index" in teacher_view.json()["questions"][0]

    # --- МОДУЛЬ 6: Студенттің тест тапсыруы ---
    # Жауаптар саны сәйкес келмесе -> 400
    fail_attempt = client.post(
        f"/api/quizzes/{quiz_id}/attempts",
        json={"answers": [0]},  # 2 сұраққа 1 жауап
        headers={"X-User-Id": str(student_1.id)},
    )
    assert fail_attempt.status_code == 400

    # Сәтті тапсыру (0 - дұрыс, 1 - дұрыс => 2/2 балл)
    attempt_res = client.post(
        f"/api/quizzes/{quiz_id}/attempts",
        json={"answers": [0, 1]},
        headers={"X-User-Id": str(student_1.id)},
    )
    assert attempt_res.status_code == 201
    att_data = attempt_res.json()
    assert att_data["score"] == 2
    assert att_data["total_questions"] == 2

    # GET /api/attempts/me -> 200
    my_attempts = client.get("/api/attempts/me", headers={"X-User-Id": str(student_1.id)})
    assert my_attempts.status_code == 200
    assert len(my_attempts.json()) >= 1
    assert my_attempts.json()[0]["quiz_id"] == quiz_id


def test_publish_empty_quiz_fails(teacher_1: User) -> None:
    # Сұрақсыз тест құру
    cr = client.post(
        "/api/quizzes",
        json={"title": "Бос тест"},
        headers={"X-User-Id": str(teacher_1.id)},
    )
    q_id = cr.json()["id"]

    # Сұрақсыз тестті жариялауға болмайды -> 400
    pub_fail = client.post(
        f"/api/quizzes/{q_id}/publish",
        headers={"X-User-Id": str(teacher_1.id)},
    )
    assert pub_fail.status_code == 400
