from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.enums import ProgressStatus
from models.learner_lesson_progress import LearnerLessonProgress
from models.learning_content import LearningContent
from models.topic import Topic
from repositories.learner_lesson_progress import (
    LearnerLessonProgressRepository,
)
from schemas.learner_lesson_progress import LessonProgressUpdate


class LearnerLessonProgressService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = LearnerLessonProgressRepository(db)

    def _validate_topic_and_content(
        self,
        *,
        topic_id: UUID,
        content_id: UUID,
    ) -> None:
        topic = self.db.scalar(select(Topic).where(Topic.topic_id == topic_id))
        if topic is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Topic not found",
            )

        content = self.db.scalar(
            select(LearningContent).where(LearningContent.content_id == content_id)
        )
        if content is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning content not found",
            )

        if content.topic_id != topic_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Learning content does not belong to this topic",
            )

    def get_progress(
        self,
        *,
        student_id: UUID,
        topic_id: UUID,
        content_id: UUID,
    ) -> LearnerLessonProgress:
        self._validate_topic_and_content(
            topic_id=topic_id,
            content_id=content_id,
        )

        progress = self.repository.get_by_student_and_content(
            student_id=student_id,
            content_id=content_id,
        )

        if progress is None or progress.topic_id != topic_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson progress not found",
            )

        return progress

    def upsert_progress(
        self,
        *,
        student_id: UUID,
        topic_id: UUID,
        content_id: UUID,
        payload: LessonProgressUpdate,
    ) -> LearnerLessonProgress:
        self._validate_topic_and_content(
            topic_id=topic_id,
            content_id=content_id,
        )

        progress = self.repository.get_by_student_and_content(
            student_id=student_id,
            content_id=content_id,
        )

        now = datetime.now(timezone.utc)

        if progress is None:
            progress = LearnerLessonProgress(
                lesson_progress_id=uuid4(),
                student_id=student_id,
                topic_id=topic_id,
                content_id=content_id,
                status=payload.status,
                last_viewed_at=payload.last_viewed_at or now,
                completed_at=(
                    now if payload.status == ProgressStatus.COMPLETED else None
                ),
            )
            return self.repository.create(progress)

        if progress.topic_id != topic_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Existing progress belongs to a different topic",
            )

        progress.status = payload.status
        progress.last_viewed_at = payload.last_viewed_at or now
        progress.completed_at = (
            progress.completed_at or now
            if payload.status == ProgressStatus.COMPLETED
            else None
        )

        return self.repository.save(progress)
