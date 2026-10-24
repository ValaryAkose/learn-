from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.enums import AssessmentStatus
from models.learner_assessment import LearnerAssessment


class LearnerAssessmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        assessment: LearnerAssessment,
    ) -> LearnerAssessment:
        try:
            self.db.add(assessment)
            self.db.commit()
            self.db.refresh(assessment)
            return assessment
        except Exception:
            self.db.rollback()
            raise

    def get_by_id(
        self,
        assessment_id: UUID,
    ) -> LearnerAssessment | None:
        return self.db.scalar(
            select(LearnerAssessment).where(
                LearnerAssessment.assessment_id == assessment_id
            )
        )

    def get_by_client_attempt(
        self,
        student_id: UUID,
        client_attempt_id: UUID,
    ) -> LearnerAssessment | None:
        return self.db.scalar(
            select(LearnerAssessment).where(
                LearnerAssessment.student_id == student_id,
                LearnerAssessment.client_attempt_id == client_attempt_id,
            )
        )

    def get_latest_attempt_number(
        self,
        student_id: UUID,
        subject_name,
        assessment_type,
        topic_id: UUID | None,
    ) -> int:
        statement = select(LearnerAssessment.attempt_number).where(
            LearnerAssessment.student_id == student_id,
            LearnerAssessment.subject_name == subject_name,
            LearnerAssessment.assessment_type == assessment_type,
        )

        if topic_id is None:
            statement = statement.where(LearnerAssessment.topic_id.is_(None))
        else:
            statement = statement.where(LearnerAssessment.topic_id == topic_id)

        latest_number = self.db.scalar(
            statement.order_by(LearnerAssessment.attempt_number.desc()).limit(1)
        )
        return (latest_number or 0) + 1

    def list_by_student(
        self,
        student_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[LearnerAssessment]:
        statement = (
            select(LearnerAssessment)
            .where(LearnerAssessment.student_id == student_id)
            .order_by(LearnerAssessment.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def list_recent_completed(
        self,
        student_id: UUID,
        limit: int = 5,
    ) -> list[LearnerAssessment]:
        statement = (
            select(LearnerAssessment)
            .where(
                LearnerAssessment.student_id == student_id,
                LearnerAssessment.status == AssessmentStatus.COMPLETED,
            )
            .order_by(LearnerAssessment.completed_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[LearnerAssessment]:
        statement = (
            select(LearnerAssessment)
            .order_by(LearnerAssessment.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def update(
        self,
        assessment: LearnerAssessment,
    ) -> LearnerAssessment:
        try:
            self.db.commit()
            self.db.refresh(assessment)
            return assessment
        except Exception:
            self.db.rollback()
            raise
