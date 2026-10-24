from uuid import UUID
from repositories.learner_progress_repository import LearnerProgressRepository
from models.learner_progress import LearnerProgress
from schemas.learners_progress import LearnerProgressCreate, LearnerProgressUpdate


class LearnerProgressService:
    def __init__(self, repository: LearnerProgressRepository):
        self.repository = repository

    def get_progress(self, student_id: UUID) -> list[LearnerProgress]:
        return self.repository.get_student_progress(student_id)

    def create_progress(self, payload: LearnerProgressCreate) -> LearnerProgress:
        progress = self.repository.get_or_create(
            student_id=payload.student_id,
            topic_id=payload.topic_id,
            subject_name=payload.subject_name,
        )
        return progress

    def list_all_progress(
        self, skip: int = 0, limit: int = 100
    ) -> list[LearnerProgress]:
        return self.repository.list_all(skip=skip, limit=limit)

    def get_or_create_progress(
        self, student_id: UUID, topic_id: UUID, subject_name: str
    ):
        return self.repository.get_or_create(student_id, topic_id, subject_name)

    def update_progress(
        self, progress: LearnerProgress, update: LearnerProgressUpdate
    ) -> LearnerProgress:
        if update.progress_status is not None:
            progress.progress_status = update.progress_status
        if update.latest_evaluation is not None:
            progress.latest_evaluation = update.latest_evaluation
        if update.recommendation_reason is not None:
            progress.recommendation_reason = update.recommendation_reason
        return self.repository.update(progress)

    def get_offline_package(self, student_id: UUID):
        progress = self.repository.get_student_progress(student_id)
        if not progress:
            return None
        return {"student_id": str(student_id), "items": []}

    def get_admin_dashboard(self):
        all_progress = self.repository.list_all(skip=0, limit=1000)
        if not all_progress:
            return None
        return {
            "total_learners": len(set(p.student_id for p in all_progress)),
            "total_progress_records": len(all_progress),
        }
