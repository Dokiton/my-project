from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.question import Question
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.user import User
from app.schemas.attempt import QuizAttemptCreate, QuizAttemptRead
from app.schemas.question import (
    QuestionCreate,
    QuestionReadStudent,
    QuestionReadTeacher,
)
from app.schemas.quiz import (
    QuizCreate,
    QuizDetailStudent,
    QuizDetailTeacher,
    QuizRead,
    QuizUpdate,
)

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])


@router.get("", response_model=list[QuizRead], summary="Тесттер тізімін алу (рөлге байланысты)")
def list_quizzes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[QuizRead]:
    statement = select(Quiz)
    if current_user.role == "student":
        # Студент тек жарияланған тесттерді көреді
        statement = statement.where(Quiz.is_published.is_(True))
    elif current_user.role == "teacher":
        # Оқытушы өзінікін және жарияланғандарды көреді
        statement = statement.where(
            or_(Quiz.author_id == current_user.id, Quiz.is_published.is_(True))
        )
    # admin бәрін көреді
    statement = statement.order_by(Quiz.created_at.desc())
    quizzes = db.scalars(statement).all()
    return [QuizRead.model_validate(q) for q in quizzes]


@router.post("", response_model=QuizRead, status_code=status.HTTP_201_CREATED, summary="Жаңа тест құру")
def create_quiz(
    quiz_in: QuizCreate,
    current_user: User = Depends(require_roles("teacher", "admin")),
    db: Session = Depends(get_db),
) -> QuizRead:
    quiz = Quiz(
        title=quiz_in.title,
        description=quiz_in.description,
        author_id=current_user.id,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return QuizRead.model_validate(quiz)


@router.get("/{id}", summary="Тест мәліметін алу (студентке дұрыс жауапсыз)")
def get_quiz(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statement = (
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .where(Quiz.id == id)
    )
    quiz = db.scalars(statement).first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тест табылмады",
        )

    # Студент жарияланбаған тестті көре алмайды
    if current_user.role == "student" and not quiz.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тест табылмады",
        )

    # Студентке дұрыс жауаптары жоқ нұсқасы қайтарылады
    if current_user.role == "student":
        questions_data = [
            QuestionReadStudent.model_validate(q) for q in quiz.questions
        ]
        return QuizDetailStudent(
            id=quiz.id,
            title=quiz.title,
            description=quiz.description,
            is_published=quiz.is_published,
            author_id=quiz.author_id,
            created_at=quiz.created_at,
            questions=questions_data,
        )

    # Оқытушы мен админге толық қайтарылады
    questions_data = [
        QuestionReadTeacher.model_validate(q) for q in quiz.questions
    ]
    return QuizDetailTeacher(
        id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        is_published=quiz.is_published,
        author_id=quiz.author_id,
        created_at=quiz.created_at,
        questions=questions_data,
    )


@router.patch("/{id}", response_model=QuizRead, summary="Тестті жаңарту (тек өз тесті немесе админ)")
def update_quiz(
    id: UUID,
    quiz_in: QuizUpdate,
    current_user: User = Depends(require_roles("teacher", "admin")),
    db: Session = Depends(get_db),
) -> QuizRead:
    quiz = db.get(Quiz, id)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тест табылмады",
        )

    # Ереже: Чужой тест: 403
    if quiz.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Бұл тестті өзгертуге құқығыңыз жоқ",
        )

    if quiz_in.title is not None:
        quiz.title = quiz_in.title
    if quiz_in.description is not None:
        quiz.description = quiz_in.description

    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return QuizRead.model_validate(quiz)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="Тестті өшіру")
def delete_quiz(
    id: UUID,
    current_user: User = Depends(require_roles("teacher", "admin")),
    db: Session = Depends(get_db),
) -> None:
    quiz = db.get(Quiz, id)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тест табылмады",
        )

    # Ереже: Чужой тест: 403
    if quiz.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Бұл тестті өшіруге құқығыңыз жоқ",
        )

    db.delete(quiz)
    db.commit()


# ==========================================
# Модуль 5: Тестке сұрақ қосу
# ==========================================


@router.post(
    "/{id}/questions",
    response_model=QuestionReadTeacher,
    status_code=status.HTTP_201_CREATED,
    summary="Тестке жаңа сұрақ қосу",
)
def add_question_to_quiz(
    id: UUID,
    q_in: QuestionCreate,
    current_user: User = Depends(require_roles("teacher", "admin")),
    db: Session = Depends(get_db),
) -> QuestionReadTeacher:
    quiz = db.get(Quiz, id)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тест табылмады",
        )

    # Ереже: Чужой тест: 403
    if quiz.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Басқа оқытушының тестіне сұрақ қоса алмайсыз",
        )

    # Ереже: В опубликованный тест нельзя: 400
    if quiz.is_published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Жарияланған тестке сұрақ қосуға болмайды",
        )

    # Ереже: correct_index больше числа вариантов: 400
    if q_in.correct_index < 0 or q_in.correct_index >= len(q_in.options):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Дұрыс жауап индексі нұсқалар санынан аспауы керек",
        )

    question = Question(
        quiz_id=quiz.id,
        text=q_in.text,
        options=q_in.options,
        correct_index=q_in.correct_index,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return QuestionReadTeacher.model_validate(question)


# ==========================================
# Модуль 6: Жариялау және тапсыру
# ==========================================


@router.post("/{id}/publish", response_model=QuizRead, summary="Тестті жариялау")
def publish_quiz(
    id: UUID,
    current_user: User = Depends(require_roles("teacher", "admin")),
    db: Session = Depends(get_db),
) -> QuizRead:
    statement = (
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .where(Quiz.id == id)
    )
    quiz = db.scalars(statement).first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тест табылмады",
        )

    # Ереже: Чужой тест: 403
    if quiz.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Бұл тестті жариялауға құқығыңыз жоқ",
        )

    # Ереже: Тест без вопросов: 400
    if len(quiz.questions) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сұрақтары жоқ тестті жариялауға болмайды",
        )

    quiz.is_published = True
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return QuizRead.model_validate(quiz)


@router.post(
    "/{id}/attempts",
    response_model=QuizAttemptRead,
    status_code=status.HTTP_201_CREATED,
    summary="Студенттің тест тапсыруы",
)
def submit_quiz_attempt(
    id: UUID,
    attempt_in: QuizAttemptCreate,
    current_user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
) -> QuizAttemptRead:
    statement = (
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .where(Quiz.id == id)
    )
    quiz = db.scalars(statement).first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тест табылмады",
        )

    # Ереже: Жарияланбаған тестке тапсыруға болмайды
    if not quiz.is_published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Бұл тест әлі жарияланбаған",
        )

    # Ереже: Если число ответов не совпадает с числом вопросов: 400
    if len(attempt_in.answers) != len(quiz.questions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Жауаптар саны сұрақтар санымен сәйкес келмейді",
        )

    # Баллды есептеу
    score = 0
    for idx, question in enumerate(quiz.questions):
        if attempt_in.answers[idx] == question.correct_index:
            score += 1

    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=current_user.id,
        answers=attempt_in.answers,
        score=score,
        total_questions=len(quiz.questions),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return QuizAttemptRead.model_validate(attempt)
