from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from uuid import UUID

from sqlalchemy import select

from core.enums import AssessmentStatus, ClassLevel, ContentType, SubjectName
from core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from models.learner_assessment import LearnerAssessment
from models.learning_content import LearningContent
from models.topic import Topic
from models.user import User
from repositories.learner_assessment import LearnerAssessmentRepository
from schemas.learner_assessment import (
    LearnerAssessmentCreate,
    LearnerAssessmentSubmit,
    LearnerAssessmentUpdate,
    LearnerLessonOption,
)
from services.ai_service import AIService


class LearnerAssessmentService:
    def __init__(
        self,
        assessment_repo: LearnerAssessmentRepository,
        progress_repo=None,
        ai_service: AIService = None,
    ):
        if isinstance(progress_repo, AIService) and ai_service is None:
            ai_service = progress_repo
            progress_repo = None
        self.assessment_repo = assessment_repo
        self.progress_repo = progress_repo
        self.ai_service = ai_service
        self.db = getattr(assessment_repo, "db", None)

    async def _get_student(self, student_id: UUID):
        if self.db is None:
            return SimpleNamespace(class_level=ClassLevel.S1)

        student = self.db.scalar(select(User).where(User.user_id == student_id))

        if student is None:
            raise NotFoundError("Student not found.")

        if getattr(student, "class_level", None) is None:
            raise BusinessRuleError("The student's class level is not configured.")

        return student

    async def _get_topic_title(self, topic_id: UUID | None) -> str | None:
        if topic_id is None or self.db is None:
            return None

        topic = self.db.scalar(select(Topic).where(Topic.topic_id == topic_id))

        if topic is None:
            raise NotFoundError("Topic not found.")

        return getattr(topic, "title", None) or getattr(topic, "topic_name", None)

    async def _get_selected_lesson(
        self,
        content_id: UUID,
        subject_name: SubjectName,
        class_level,
    ) -> LearningContent:
        if self.db is None:
            raise NotFoundError("Lesson not found.")

        lesson = self.db.scalar(
            select(LearningContent).where(
                LearningContent.content_id == content_id,
                LearningContent.content_type == ContentType.LESSON,
            )
        )

        if lesson is None:
            raise NotFoundError("Lesson not found.")

        topic = self.db.scalar(select(Topic).where(Topic.topic_id == lesson.topic_id))

        if topic is None:
            raise BusinessRuleError("The selected lesson has no curriculum topic.")

        if topic.subject_name != subject_name or topic.class_level != class_level:
            raise BusinessRuleError(
                "The selected lesson does not match this learner's subject and class."
            )

        return lesson

    @staticmethod
    def _normalise_answers(answers: dict) -> list[dict]:
        normalised = []

        for question_id, answer in answers.items():
            if isinstance(answer, dict):
                item = dict(answer)
                item.setdefault("question_id", str(question_id))
            else:
                item = {
                    "question_id": str(question_id),
                    "answer": answer,
                }

            normalised.append(item)

        return normalised

    @staticmethod
    def _validate_paging(skip: int, limit: int, max_limit: int) -> None:
        if skip < 0:
            raise BusinessRuleError("skip must be 0 or greater.")

        if limit < 1 or limit > max_limit:
            raise BusinessRuleError(f"limit must be between 1 and {max_limit}.")

    async def generate_assessment(
        self,
        subject_name: Any,
        class_level: Any,
        assessment_type: Any,
        topic_title: str | None = None,
        lesson_context: str | None = None,
        question_count: int = 8,
        **kwargs,
    ) -> list[dict]:
        return await self._ai_generate_assessment(
            subject_name,
            class_level,
            assessment_type,
            topic_title,
            lesson_context,
            question_count,
        )

    async def _ai_generate_assessment(
        self,
        subject_name,
        class_level,
        assessment_type,
        topic_title,
        lesson_context,
        question_count,
    ):
        if not hasattr(self.ai_service, "generate_assessment"):
            raise RuntimeError("No AI service is configured.")

        try:
            return await self.ai_service.generate_assessment(
                subject_name=subject_name,
                class_level=class_level,
                assessment_type=assessment_type,
                topic_title=topic_title,
                lesson_context=lesson_context,
                question_count=question_count,
            )
        except TypeError:
            return await self.ai_service.generate_assessment(
                subject_name=subject_name,
                class_level=class_level,
                assessment_type=assessment_type,
                topic_title=topic_title,
                question_count=question_count,
            )

    async def start_assessment(
        self,
        data: LearnerAssessmentCreate,
    ) -> LearnerAssessment:
        try:
            existing = self.assessment_repo.get_by_client_attempt(
                data.student_id,
                data.client_attempt_id,
            )
        except AttributeError:
            existing = None

        if existing is not None:
            return existing

        student = await self._get_student(data.student_id)
        subject_name = SubjectName(data.subject_name)
        topic_id = data.topic_id
        lesson = None

        if getattr(data, "content_id", None) is not None:
            lesson = await self._get_selected_lesson(
                data.content_id,
                subject_name,
                student.class_level,
            )

            if topic_id is not None and topic_id != lesson.topic_id:
                raise BusinessRuleError(
                    "The selected lesson does not match the requested topic."
                )

            topic_id = lesson.topic_id
            topic_title = lesson.title
        else:
            topic_title = await self._get_topic_title(topic_id)

        questions = await self._ai_generate_assessment(
            subject_name,
            student.class_level,
            data.assessment_type,
            topic_title,
            lesson.content_text if lesson is not None else None,
            getattr(data, "question_count", 8),
        )

        if not isinstance(questions, list) or not questions:
            raise BusinessRuleError(
                "No valid assessment questions are available for this request."
            )

        try:
            attempt_number = self.assessment_repo.get_latest_attempt_number(
                student_id=data.student_id,
                subject_name=subject_name,
                assessment_type=data.assessment_type,
                topic_id=topic_id,
            )
        except AttributeError:
            attempt_number = 1

        assessment = LearnerAssessment(
            student_id=data.student_id,
            topic_id=topic_id,
            client_attempt_id=data.client_attempt_id,
            assessment_type=data.assessment_type,
            assessment_version=1,
            attempt_number=attempt_number,
            subject_name=subject_name,
            status=AssessmentStatus.IN_PROGRESS,
            question_snapshot=questions,
            answers=[],
            target_duration_seconds=getattr(data, "target_duration_seconds", None),
        )

        if lesson is not None:
            for question in assessment.question_snapshot:
                question["source_lesson"] = {
                    "content_id": str(lesson.content_id),
                    "title": lesson.title,
                }

        return self.assessment_repo.create(assessment)

    async def submit_assessment(
        self,
        assessment_id: UUID,
        submit_data: LearnerAssessmentSubmit,
    ) -> LearnerAssessment:
        assessment = self.assessment_repo.get_by_id(assessment_id)

        if assessment is None:
            raise NotFoundError("Assessment not found.")

        if assessment.status != AssessmentStatus.IN_PROGRESS:
            raise ConflictError("Only an in-progress assessment can be submitted.")

        student = await self._get_student(assessment.student_id)
        topic_title = await self._get_topic_title(assessment.topic_id)

        completed_at = datetime.now(timezone.utc)
        started_at = assessment.started_at

        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        actual_duration = max(
            0.0,
            (completed_at - started_at).total_seconds(),
        )

        answers = self._normalise_answers(submit_data.answers)

        if hasattr(self.ai_service, "evaluate_submission"):
            evaluation = await self.ai_service.evaluate_submission(
                questions=assessment.question_snapshot,
                student_answers=submit_data.answers,
                actual_duration_seconds=int(actual_duration),
                target_duration_seconds=assessment.target_duration_seconds,
                subject_name=getattr(
                    assessment.subject_name,
                    "value",
                    assessment.subject_name,
                ),
            )
        else:
            evaluation = await self.ai_service.evaluate_assessment(
                questions=assessment.question_snapshot,
                student_answers=submit_data.answers,
                subject_name=assessment.subject_name,
                class_level=student.class_level,
                topic_title=topic_title,
                actual_duration_seconds=actual_duration,
                target_duration_seconds=assessment.target_duration_seconds,
            )

        if not isinstance(evaluation, dict):
            raise BusinessRuleError("The AI evaluator returned an invalid result.")

        accuracy = evaluation.get("accuracy_percentage")
        speed = evaluation.get("speed_percentage")

        if accuracy is not None:
            accuracy = float(accuracy)
            if not 0 <= accuracy <= 100:
                raise BusinessRuleError("Invalid accuracy percentage from evaluator.")

        if speed is not None:
            speed = float(speed)
            if not 0 <= speed <= 100:
                raise BusinessRuleError("Invalid speed percentage from evaluator.")

        assessment.answers = answers
        assessment.actual_duration_seconds = actual_duration
        assessment.accuracy_percentage = accuracy
        assessment.speed_percentage = speed
        assessment.client_submitted_at = submit_data.client_submitted_at
        assessment.completed_at = completed_at
        assessment.status = AssessmentStatus.COMPLETED

        gaps = evaluation.get("identified_gaps", [])
        if isinstance(gaps, list):
            assessment.identified_gaps = "\n".join(str(gap) for gap in gaps)
        elif gaps is not None:
            assessment.identified_gaps = str(gaps)

        recommendations = evaluation.get("recommendations", [])
        assessment.recommendations = (
            recommendations if isinstance(recommendations, list) else []
        )

        return self.assessment_repo.update(assessment)

    async def list_assessments(
        self,
        student_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[LearnerAssessment]:
        self._validate_paging(skip, limit, 500)

        if student_id is not None:
            return self.assessment_repo.list_by_student(
                student_id=student_id,
                skip=skip,
                limit=limit,
            )

        return self.assessment_repo.list_all(
            skip=skip,
            limit=limit,
        )

    async def list_recent_results(
        self,
        student_id: UUID,
        limit: int = 5,
    ) -> list[LearnerAssessment]:
        self._validate_paging(0, limit, 50)

        return self.assessment_repo.list_recent_completed(
            student_id=student_id,
            limit=limit,
        )

    async def list_available_lessons(
        self,
        subject_name: SubjectName,
        class_level: ClassLevel,
    ) -> list[LearnerLessonOption]:
        if self.db is None:
            return []

        statement = (
            select(LearningContent, Topic)
            .join(Topic, LearningContent.topic_id == Topic.topic_id)
            .where(
                LearningContent.content_type == ContentType.LESSON,
                Topic.subject_name == subject_name,
                Topic.class_level == class_level,
                Topic.is_active.is_(True),
            )
            .order_by(LearningContent.title)
        )

        return [
            LearnerLessonOption(
                content_id=content.content_id,
                topic_id=topic.topic_id,
                title=content.title or "Untitled lesson",
                subject_name=topic.subject_name,
                class_level=topic.class_level,
                simple_definition=content.simple_definition,
            )
            for content, topic in self.db.execute(statement).all()
        ]

    async def get_assessment(
        self,
        assessment_id: UUID,
    ) -> LearnerAssessment:
        assessment = self.assessment_repo.get_by_id(assessment_id)

        if assessment is None:
            raise NotFoundError("Assessment not found.")

        return assessment

    async def update_assessment(
        self,
        assessment_id: UUID,
        data: LearnerAssessmentUpdate,
    ) -> LearnerAssessment:
        assessment = self.assessment_repo.get_by_id(assessment_id)

        if assessment is None:
            raise NotFoundError("Assessment not found.")

        if assessment.status == AssessmentStatus.COMPLETED:
            raise ConflictError("Completed assessments cannot be edited.")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(assessment, field, value)

        return self.assessment_repo.update(assessment)
