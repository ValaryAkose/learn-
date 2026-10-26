from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.learner_progress import LearnerProgress


class LearnerProgressRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(
        self, student_id: UUID, topic_id: UUID, subject_name: str
    ) -> LearnerProgress:
        result = self.db.execute(
            select(LearnerProgress).where(
                LearnerProgress.student_id == student_id,
                LearnerProgress.topic_id == topic_id,
            )
        )
        progress = result.scalar_one_or_none()
        if not progress:
            progress = LearnerProgress(
                student_id=student_id,
                topic_id=topic_id,
                subject_name=subject_name,
            )
            self.db.add(progress)
            self.db.commit()
            self.db.refresh(progress)
        return progress

    def get_student_progress(self, student_id: UUID) -> list[LearnerProgress]:
        result = self.db.execute(
            select(LearnerProgress).where(LearnerProgress.student_id == student_id)
        )
        return list(result.scalars().all())

    def list_all(self, skip: int = 0, limit: int = 100) -> list[LearnerProgress]:
        result = self.db.execute(select(LearnerProgress).offset(skip).limit(limit))
        return list(result.scalars().all())

    def update(self, progress: LearnerProgress) -> LearnerProgress:
        self.db.commit()
        self.db.refresh(progress)
        return progress

    def delete(self, student_id: UUID, topic_id: UUID) -> bool:
        result = self.db.execute(
            select(LearnerProgress).where(
                LearnerProgress.student_id == student_id,
                LearnerProgress.topic_id == topic_id,
            )
        )
        progress = result.scalar_one_or_none()
        if not progress:
            return False
        self.db.delete(progress)
        self.db.commit()
        return True
