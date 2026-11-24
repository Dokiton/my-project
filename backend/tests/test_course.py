import uuid
import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import engine
from app.models.course import Course
from app.models.user import User
from app.repositories.course_repository import CourseRepository
from app.schemas.course import CourseCreate, CourseRead, CourseUpdate

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
        email=f"teacher_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Teacher User",
        role="teacher",
        hashed_password="dummy_hashed_password",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# --- Schema Tests ---


def test_course_create_schema_valid() -> None:
    data = CourseCreate(title="Python Programming", description="Introductory course")
    assert data.title == "Python Programming"
    assert data.description == "Introductory course"


def test_course_create_schema_without_description() -> None:
    data = CourseCreate(title="Algorithms")
    assert data.title == "Algorithms"
    assert data.description is None


def test_course_create_schema_validation_error() -> None:
    with pytest.raises(ValidationError):
        CourseCreate(title="Py")  # < 3 chars


def test_course_update_schema() -> None:
    update_data = CourseUpdate(title="Advanced Python")
    assert update_data.title == "Advanced Python"
    assert update_data.description is None

    empty_update = CourseUpdate()
    assert empty_update.title is None
    assert empty_update.description is None


def test_course_read_schema_from_orm(teacher: User, db_session: Session) -> None:
    repo = CourseRepository(db_session)
    course_orm = Course(
        title="Web Development",
        description="FastAPI + React",
        teacher_id=teacher.id,
    )
    saved = repo.create(course_orm)
    schema = CourseRead.model_validate(saved)
    assert schema.id == saved.id
    assert schema.title == "Web Development"
    assert schema.description == "FastAPI + React"
    assert schema.teacher_id == teacher.id
    assert schema.created_at is not None


# --- Repository Tests ---


def test_course_repository_create_and_get(
    db_session: Session, teacher: User
) -> None:
    repo = CourseRepository(db_session)
    course = Course(
        title="Database Systems",
        description="PostgreSQL deep dive",
        teacher_id=teacher.id,
    )
    created = repo.create(course)
    assert created.id is not None
    assert created.title == "Database Systems"

    fetched = repo.get(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.teacher_id == teacher.id


def test_course_repository_get_nonexistent(db_session: Session) -> None:
    repo = CourseRepository(db_session)
    assert repo.get(uuid.uuid4()) is None


def test_course_repository_list(db_session: Session, teacher: User) -> None:
    repo = CourseRepository(db_session)
    c1 = Course(title="Course 1", teacher_id=teacher.id)
    c2 = Course(title="Course 2", teacher_id=teacher.id)
    repo.create(c1)
    repo.create(c2)

    courses = repo.list(offset=0, limit=10)
    assert len(courses) >= 2
    titles = [c.title for c in courses]
    assert "Course 1" in titles
    assert "Course 2" in titles


def test_course_repository_save(db_session: Session, teacher: User) -> None:
    repo = CourseRepository(db_session)
    course = Course(title="Old Title", teacher_id=teacher.id)
    repo.create(course)

    course.title = "New Title"
    course.description = "Updated description"
    saved = repo.save(course)

    assert saved.title == "New Title"
    assert saved.description == "Updated description"

    refetched = repo.get(course.id)
    assert refetched is not None
    assert refetched.title == "New Title"


def test_course_repository_delete(db_session: Session, teacher: User) -> None:
    repo = CourseRepository(db_session)
    course = Course(title="To be deleted", teacher_id=teacher.id)
    repo.create(course)

    course_id = course.id
    repo.delete(course)

    assert repo.get(course_id) is None
