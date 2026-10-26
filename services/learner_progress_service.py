from uuid import UUID

from core.exceptions import BadRequestError, NotFoundError
from repositories.learner_progress_repository import LearnerProgressRepository
from models.learner_progress import LearnerProgress
from schemas.learners_progress import LearnerProgressCreate, LearnerProgressUpdate


class LearnerProgressService:
    def __init__(self, repository: LearnerProgressRepository):
        self.repository = repository

    def get_progress(self, student_id: UUID) -> list[LearnerProgress]:
        progress = self.repository.get_student_progress(student_id)
        if not progress:
            raise NotFoundError("Progress not found")
        return progress

    def create_progress(self, payload: LearnerProgressCreate) -> LearnerProgress:
        try:
            return self.repository.get_or_create(
                student_id=payload.student_id,
                topic_id=payload.topic_id,
                subject_name=payload.subject_name,
            )
        except Exception as exc:
            raise BadRequestError(str(exc)) from exc

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
