from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.user import User
from app.schemas.course import CourseCreate, CourseRead
from app.schemas.enrollment import EnrolledStudentItem, EnrollmentRead

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED, summary="Жаңа курс құру")
def create_course(
    course_in: CourseCreate,
    current_user: User = Depends(require_roles("teacher", "admin")),
    db: Session = Depends(get_db),
) -> CourseRead:
    course = Course(
        title=course_in.title,
        description=course_in.description,
        teacher_id=current_user.id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return CourseRead.model_validate(course)


@router.get("", response_model=list[CourseRead], summary="Курстар каталогы")
def list_courses(
    db: Session = Depends(get_db),
) -> list[CourseRead]:
    statement = select(Course).order_by(Course.created_at.desc())
    courses = db.scalars(statement).all()
    return [CourseRead.model_validate(c) for c in courses]


@router.get("/my", response_model=list[CourseRead], summary="Менің курстарым")
def get_my_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CourseRead]:
    if current_user.role == "student":
        # Студент жазылған курстар
        statement = (
            select(Course)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .where(Enrollment.student_id == current_user.id)
            .order_by(Enrollment.enrolled_at.desc())
        )
    elif current_user.role == "teacher":
        # Оқытушының өз курстары
        statement = select(Course).where(Course.teacher_id == current_user.id).order_by(Course.created_at.desc())
    else:
        # Admin барлығын көреді
        statement = select(Course).order_by(Course.created_at.desc())

    courses = db.scalars(statement).all()
    return [CourseRead.model_validate(c) for c in courses]


@router.get("/{id}", response_model=CourseRead, summary="Курс мәліметін алу")
def get_course(
    id: UUID,
    db: Session = Depends(get_db),
) -> CourseRead:
    course = db.get(Course, id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курс табылмады",
        )
    return CourseRead.model_validate(course)


@router.post("/{id}/enroll", response_model=EnrollmentRead, status_code=status.HTTP_201_CREATED, summary="Курсқа жазылу")
def enroll_in_course(
    id: UUID,
    current_user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
) -> EnrollmentRead:
    course = db.get(Course, id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курс табылмады",
        )

    # US-1.4: Қайта жазылуға тыйым
    existing = db.scalars(
        select(Enrollment).where(
            Enrollment.course_id == id, Enrollment.student_id == current_user.id
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сіз бұл курсқа бұрыннан жазылғансыз",
        )

    enrollment = Enrollment(
        course_id=id,
        student_id=current_user.id,
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return EnrollmentRead.model_validate(enrollment)


@router.get("/{id}/students", response_model=list[EnrolledStudentItem], summary="Курстағы студенттер тізімі")
def get_course_students(
    id: UUID,
    current_user: User = Depends(require_roles("teacher", "admin")),
    db: Session = Depends(get_db),
) -> list[EnrolledStudentItem]:
    course = db.get(Course, id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курс табылмады",
        )

    # Оқытушы тек өз курсының студенттерін көре алады
    if course.teacher_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Бұл курстың студенттер тізімін көруге рұқсатыңыз жоқ",
        )

    statement = (
        select(Enrollment)
        .options(selectinload(Enrollment.student))
        .where(Enrollment.course_id == id)
        .order_by(Enrollment.enrolled_at.asc())
    )
    enrollments = db.scalars(statement).all()

    return [
        EnrolledStudentItem(
            student_id=e.student_id,
            student_name=e.student.full_name if e.student else "Белгісіз",
            student_email=e.student.email if e.student else "",
            enrolled_at=e.enrolled_at,
        )
        for e in enrollments
    ]
