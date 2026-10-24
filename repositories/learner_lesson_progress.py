from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.learner_lesson_progress import LearnerLessonProgress


class LearnerLessonProgressRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_student_and_content(
        self,
        *,
        student_id: UUID,
        content_id: UUID,
    ) -> LearnerLessonProgress | None:
        statement = select(LearnerLessonProgress).where(
            LearnerLessonProgress.student_id == student_id,
            LearnerLessonProgress.content_id == content_id,
        )
        return self.db.scalar(statement)

    def create(
        self,
        progress: LearnerLessonProgress,
    ) -> LearnerLessonProgress:
        self.db.add(progress)
        self.db.flush()
        self.db.refresh(progress)
        return progress

    def save(
        self,
        progress: LearnerLessonProgress,
    ) -> LearnerLessonProgress:
        self.db.add(progress)
        self.db.flush()
        self.db.refresh(progress)
        return progress
