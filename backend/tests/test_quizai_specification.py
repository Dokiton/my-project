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
        keycloak_id=f"kc-{uuid.uuid4().hex[:12]}",
        email=f"admin_{uuid.uuid4().hex[:8]}@edu.kz",
        full_name="Admin User",
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def teacher_1(db_session: Session) -> User:
    user = User(
        keycloak_id=f"kc-{uuid.uuid4().hex[:12]}",
        email=f"teacher1_{uuid.uuid4().hex[:8]}@edu.kz",
        full_name="Teacher One",
        role="teacher",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def teacher_2(db_session: Session) -> User:
    user = User(
        keycloak_id=f"kc-{uuid.uuid4().hex[:12]}",
        email=f"teacher2_{uuid.uuid4().hex[:8]}@edu.kz",
        full_name="Teacher Two",
        role="teacher",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def student_1(db_session: Session) -> User:
    user = User(
        keycloak_id=f"kc-{uuid.uuid4().hex[:12]}",
        email=f"student1_{uuid.uuid4().hex[:8]}@edu.kz",
        full_name="Student One",
        role="student",
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
# Модуль 1–2: Keycloak Auth (тек GET /api/auth/me; ескі register/login өшірілген)
# ==============================================================================


def test_auth_me_and_legacy_endpoints_removed(student_1: User, auth_headers) -> None:
    res_unauth = client.get("/api/auth/me")
    assert res_unauth.status_code == 401

    res_me = client.get("/api/auth/me", headers=auth_headers(student_1))
    assert res_me.status_code == 200
    assert res_me.json()["id"] == str(student_1.id)
    assert res_me.json()["keycloak_id"] == student_1.keycloak_id

    # Ескі тіркелу мен логин эндпоинттері енді жоқ
    assert client.post("/api/auth/register", json={}).status_code == 404
    assert client.post("/api/auth/login", json={}).status_code == 404


# ==============================================================================
# Модуль 3: Управление пользователями (только admin)
# ==============================================================================


def test_users_list_admin_only(
    admin_user: User, teacher_1: User, student_1: User, auth_headers
) -> None:
    # Admin көре алады -> 200
    res_admin = client.get("/api/users", headers=auth_headers(admin_user))
    assert res_admin.status_code == 200
    assert isinstance(res_admin.json(), list)

    # Teacher -> 403
    res_teacher = client.get("/api/users", headers=auth_headers(teacher_1))
    assert res_teacher.status_code == 403

    # Student -> 403
    res_student = client.get("/api/users", headers=auth_headers(student_1))
    assert res_student.status_code == 403


def test_users_get_by_id(admin_user: User, student_1: User, auth_headers) -> None:
    res = client.get(
        f"/api/users/{student_1.id}", headers=auth_headers(admin_user)
    )
    assert res.status_code == 200
    assert res.json()["id"] == str(student_1.id)

    res_404 = client.get(
        f"/api/users/{uuid.uuid4()}", headers=auth_headers(admin_user)
    )
    assert res_404.status_code == 404


def test_users_patch_removed(admin_user: User, student_1: User, auth_headers) -> None:
    # Рөл Keycloak-та басқарылады, сондықтан PATCH /api/users/{id} өшірілген
    res = client.patch(
        f"/api/users/{student_1.id}",
        json={"role": "teacher"},
        headers=auth_headers(admin_user),
    )
    assert res.status_code == 405


def test_users_delete_and_cannot_delete_self(
    admin_user: User, db_session: Session, auth_headers
) -> None:
    temp_user = User(
        keycloak_id=f"kc-{uuid.uuid4().hex[:12]}",
        email="temp@edu.kz",
        full_name="Temp",
        role="student",
    )
    db_session.add(temp_user)
    db_session.commit()
    db_session.refresh(temp_user)

    # Өзін өшіруге тыйым -> 400
    res_self = client.delete(
        f"/api/users/{admin_user.id}", headers=auth_headers(admin_user)
    )
    assert res_self.status_code == 400

    # Басқаны өшіру -> 204
    res_del = client.delete(
        f"/api/users/{temp_user.id}", headers=auth_headers(admin_user)
    )
    assert res_del.status_code == 204


# ==============================================================================
# Модуль 4 & 5 & 6: Тесттер (Quiz), Сұрақтар және Тапсыру
# ==============================================================================


def test_quiz_lifecycle_modules_4_5_6(
    admin_user: User,
    teacher_1: User,
    teacher_2: User,
    student_1: User,
    auth_headers,
) -> None:
    # --- МОДУЛЬ 4: Тест құру ---
    fail_create = client.post(
        "/api/quizzes",
        json={"title": "Студент тесті"},
        headers=auth_headers(student_1),
    )
    assert fail_create.status_code == 403

    create_res = client.post(
        "/api/quizzes",
        json={"title": "Python негіздері", "description": "Сұрақ-жауап"},
        headers=auth_headers(teacher_1),
    )
    assert create_res.status_code == 201
    quiz_id = create_res.json()["id"]

    # --- МОДУЛЬ 5: Сұрақ қосу ---
    res_other_teacher_q = client.post(
        f"/api/quizzes/{quiz_id}/questions",
        json={"text": "2+2 неше?", "options": ["3", "4", "5"], "correct_index": 1},
        headers=auth_headers(teacher_2),
    )
    assert res_other_teacher_q.status_code == 403

    res_bad_idx = client.post(
        f"/api/quizzes/{quiz_id}/questions",
        json={"text": "Қате сұрақ", "options": ["А", "Б"], "correct_index": 5},
        headers=auth_headers(teacher_1),
    )
    assert res_bad_idx.status_code == 400

    q1_res = client.post(
        f"/api/quizzes/{quiz_id}/questions",
        json={
            "text": "Python-да тізім қалай жазылады?",
            "options": ["[]", "{}", "()"],
            "correct_index": 0,
        },
        headers=auth_headers(teacher_1),
    )
    assert q1_res.status_code == 201
    q1_id = q1_res.json()["id"]

    q2_res = client.post(
        f"/api/quizzes/{quiz_id}/questions",
        json={
            "text": "Сөздік қалай жазылады?",
            "options": ["[]", "{}", "()"],
            "correct_index": 1,
        },
        headers=auth_headers(teacher_1),
    )
    assert q2_res.status_code == 201

    patch_q_res = client.patch(
        f"/api/questions/{q1_id}",
        json={"text": "Python-да жаңартылған тізім?"},
        headers=auth_headers(teacher_1),
    )
    assert patch_q_res.status_code == 200

    fail_patch_q = client.patch(
        f"/api/questions/{q1_id}",
        json={"text": "Хакер сұрағы"},
        headers=auth_headers(teacher_2),
    )
    assert fail_patch_q.status_code == 403

    # --- МОДУЛЬ 6: Жариялау ---
    fail_pub = client.post(
        f"/api/quizzes/{quiz_id}/publish",
        headers=auth_headers(teacher_2),
    )
    assert fail_pub.status_code == 403

    res_list_student_before = client.get(
        "/api/quizzes", headers=auth_headers(student_1)
    )
    assert not any(q["id"] == quiz_id for q in res_list_student_before.json())

    pub_res = client.post(
        f"/api/quizzes/{quiz_id}/publish",
        headers=auth_headers(teacher_1),
    )
    assert pub_res.status_code == 200
    assert pub_res.json()["is_published"] is True

    fail_add_after_pub = client.post(
        f"/api/quizzes/{quiz_id}/questions",
        json={"text": "Кеш қосылған", "options": ["А", "Б"], "correct_index": 0},
        headers=auth_headers(teacher_1),
    )
    assert fail_add_after_pub.status_code == 400

    fail_edit_after_pub = client.patch(
        f"/api/questions/{q1_id}",
        json={"text": "Жарияланған соң өзгерту"},
        headers=auth_headers(teacher_1),
    )
    assert fail_edit_after_pub.status_code == 400

    # --- МОДУЛЬ 4: Студент тестті қарайды (дұрыс жауапсыз!) ---
    student_view = client.get(
        f"/api/quizzes/{quiz_id}", headers=auth_headers(student_1)
    )
    assert student_view.status_code == 200
    q_data_student = student_view.json()["questions"][0]
    assert "correct_index" not in q_data_student

    teacher_view = client.get(
        f"/api/quizzes/{quiz_id}", headers=auth_headers(teacher_1)
    )
    assert teacher_view.status_code == 200
    assert "correct_index" in teacher_view.json()["questions"][0]

    # --- МОДУЛЬ 6: Студенттің тест тапсыруы ---
    fail_attempt = client.post(
        f"/api/quizzes/{quiz_id}/attempts",
        json={"answers": [0]},
        headers=auth_headers(student_1),
    )
    assert fail_attempt.status_code == 400

    attempt_res = client.post(
        f"/api/quizzes/{quiz_id}/attempts",
        json={"answers": [0, 1]},
        headers=auth_headers(student_1),
    )
    assert attempt_res.status_code == 201
    att_data = attempt_res.json()
    assert att_data["score"] == 2
    assert att_data["total_questions"] == 2

    my_attempts = client.get("/api/attempts/me", headers=auth_headers(student_1))
    assert my_attempts.status_code == 200
    assert len(my_attempts.json()) >= 1
    assert my_attempts.json()[0]["quiz_id"] == quiz_id


def test_publish_empty_quiz_fails(teacher_1: User, auth_headers) -> None:
    cr = client.post(
        "/api/quizzes",
        json={"title": "Бос тест"},
        headers=auth_headers(teacher_1),
    )
    q_id = cr.json()["id"]

    pub_fail = client.post(
        f"/api/quizzes/{q_id}/publish",
        headers=auth_headers(teacher_1),
    )
    assert pub_fail.status_code == 400
