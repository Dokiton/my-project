from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.question import Question
from app.models.user import User
from app.schemas.question import QuestionReadTeacher, QuestionUpdate

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.patch("/{id}", response_model=QuestionReadTeacher, summary="Сұрақты жаңарту")
def update_question(
    id: UUID,
    q_in: QuestionUpdate,
    current_user: User = Depends(require_roles("teacher", "admin")),
    db: Session = Depends(get_db),
) -> QuestionReadTeacher:
    question = db.get(Question, id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сұрақ табылмады",
        )

    quiz = question.quiz
    # Ереже: Чужой: 403
    if quiz.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Бұл сұрақты өзгертуге құқығыңыз жоқ",
        )

    # Ереже: Опубликованный тест: 400
    if quiz.is_published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Жарияланған тесттің сұрағын өзгертуге болмайды",
        )

    # Валидация options және correct_index
    new_options = q_in.options if q_in.options is not None else question.options
    new_correct = (
        q_in.correct_index
        if q_in.correct_index is not None
        else question.correct_index
    )

    if new_correct < 0 or new_correct >= len(new_options):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Дұрыс жауап индексі нұсқалар санынан аспауы керек",
        )

    if q_in.text is not None:
        question.text = q_in.text
    if q_in.options is not None:
        question.options = q_in.options
    if q_in.correct_index is not None:
        question.correct_index = q_in.correct_index

    db.add(question)
    db.commit()
    db.refresh(question)
    return QuestionReadTeacher.model_validate(question)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="Сұрақты өшіру")
def delete_question(
    id: UUID,
    current_user: User = Depends(require_roles("teacher", "admin")),
    db: Session = Depends(get_db),
) -> None:
    question = db.get(Question, id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сұрақ табылмады",
        )

    quiz = question.quiz
    # Ереже: Чужой: 403
    if quiz.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Бұл сұрақты өшіруге құқығыңыз жоқ",
        )

    # Ереже: Опубликованный тест: 400
    if quiz.is_published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Жарияланған тесттің сұрағын өшіруге болмайды",
        )

    db.delete(question)
    db.commit()
