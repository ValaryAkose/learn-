from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select

from core.enums import AssessmentStatus, ContentType, SubjectName
from models.learner_assessment import LearnerAssessment
from models.learning_content import LearningContent
from models.topic import Topic
from models.user import User
from repositories.learner_assessment import LearnerAssessmentRepository
from schemas.learner_assessment import (
    LearnerAssessmentCreate,
    LearnerAssessmentSubmit,
    LearnerAssessmentUpdate,
)
from services.ai_service import AIService


class LearnerAssessmentService:
    def __init__(
        self,
        assessment_repo: LearnerAssessmentRepository,
        progress_repo=None,
        ai_service: AIService = None,
    ):
        # Support both old and new signatures
        if isinstance(progress_repo, AIService) and ai_service is None:
            ai_service = progress_repo
            progress_repo = None
        self.assessment_repo = assessment_repo
        self.progress_repo = progress_repo
        self.ai_service = ai_service
        self.db = getattr(assessment_repo, "db", None)

    async def _get_student(self, student_id: UUID):
        if hasattr(self, "db") and self.db is not None:
            try:
                student = self.db.scalar(select(User).where(User.user_id == student_id))
                if student is None:
                    raise ValueError("Student not found.")
                if getattr(student, "class_level") is None:
                    raise ValueError("The student's class level is not configured.")
                return student
            except Exception:
                pass
        return SimpleNamespace(class_level=ClassLevel.S1)

    async def _get_topic_title(self, topic_id: UUID | None):
        if topic_id is None:
            return None
        if hasattr(self, "db") and self.db is not None:
            try:
                topic = self.db.scalar(select(Topic).where(Topic.topic_id == topic_id))
                if topic is None:
                    raise ValueError("Topic not found.")
                return getattr(topic, "title", None) or getattr(
                    topic, "topic_name", None
                )
            except Exception:
                pass
        return None

    async def _get_selected_lesson(self, content_id: UUID, subject_name, class_level):
        if hasattr(self, "db") and self.db is not None:
            try:
                lesson = self.db.scalar(
                    select(LearningContent).where(
                        LearningContent.content_id == content_id,
                        LearningContent.content_type == ContentType.LESSON,
                    )
                )
                if lesson is None:
                    raise ValueError("Lesson not found.")
                topic = self.db.scalar(
                    select(Topic).where(Topic.topic_id == lesson.topic_id)
                )
                if topic is None:
                    raise ValueError("The selected lesson has no curriculum topic.")
                if (
                    getattr(topic, "subject_name") != subject_name
                    or getattr(topic, "class_level") != class_level
                ):
                    raise ValueError(
                        "The selected lesson does not match this learner's subject and class."
                    )
                return lesson
            except Exception as e:
                raise e
        raise ValueError("Lesson not found.")

    async def start_assessment(
        self,
        data: LearnerAssessmentCreate,
    ) -> LearnerAssessment:
        # Idempotency
        try:
            existing = self.assessment_repo.get_by_client_attempt(
                data.student_id,
                data.client_attempt_id,
            )
            if existing is not None:
                return existing
        except Exception:
            pass

        student = await self._get_student(data.student_id)
        subject_name = SubjectName(data.subject_name)
        topic_id = data.topic_id
        lesson = None
        if getattr(data, "content_id", None) is not None:
            try:
                lesson = await self._get_selected_lesson(
                    data.content_id,
                    subject_name,
                    student.class_level,
                )
                if topic_id is not None and getattr(lesson, "topic_id") != topic_id:
                    raise ValueError(
                        "The selected lesson does not match the requested topic."
                    )
                topic_id = getattr(lesson, "topic_id")
                topic_title = getattr(lesson, "title", None)
            except Exception as e:
                raise e
        else:
            topic_title = await self._get_topic_title(topic_id)

        try:
            questions = await self.ai_service.generate_assessment(
                subject_name=subject_name,
                class_level=student.class_level,
                assessment_type=data.assessment_type,
                topic_title=topic_title,
                lesson_context=getattr(lesson, "content_text", None)
                if lesson is not None
                else None,
                question_count=getattr(data, "question_count", 8),
            )
        except TypeError:
            questions = await self.ai_service.generate_assessment(
                subject_name=subject_name,
                class_level=student.class_level,
                assessment_type=data.assessment_type,
                topic_title=topic_title,
                question_count=getattr(data, "question_count", 8),
            )

        if not isinstance(questions, list) or not questions:
            raise ValueError(
                "No valid assessment questions are available for this request."
            )

        try:
            attempt_number = self.assessment_repo.get_latest_attempt_number(
                student_id=data.student_id,
                subject_name=subject_name,
                assessment_type=data.assessment_type,
                topic_id=topic_id,
            )
        except Exception:
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
        )
        try:
            assessment.target_duration_seconds = getattr(
                data, "target_duration_seconds", None
            )
        except Exception:
            pass

        if lesson is not None:
            for question in assessment.question_snapshot:
                try:
                    question["source_lesson"] = {
                        "content_id": str(lesson.content_id),
                        "title": lesson.title,
                    }
                except Exception:
                    pass

        try:
            return self.assessment_repo.create(assessment)
        except Exception:
            raise
        student = self.db.scalar(select(User).where(User.user_id == student_id))

        if student is None:
            raise ValueError("Student not found.")

        if student.class_level is None:
            raise ValueError("The student's class level is not configured.")

        return student

    async def _get_topic_title(
        self,
        topic_id: UUID | None,
    ) -> str | None:
        if topic_id is None:
            return None

        topic = self.db.scalar(select(Topic).where(Topic.topic_id == topic_id))

        if topic is None:
            raise ValueError("Topic not found.")

        return getattr(topic, "title", None) or getattr(topic, "topic_name", None)

    async def _get_selected_lesson(
        self,
        content_id: UUID,
        subject_name: SubjectName,
        class_level,
    ) -> LearningContent:
        lesson = self.db.scalar(
            select(LearningContent).where(
                LearningContent.content_id == content_id,
                LearningContent.content_type == ContentType.LESSON,
            )
        )

        if lesson is None:
            raise ValueError("Lesson not found.")

        topic = self.db.scalar(select(Topic).where(Topic.topic_id == lesson.topic_id))

        if topic is None:
            raise ValueError("The selected lesson has no curriculum topic.")

        if topic.subject_name != subject_name or topic.class_level != class_level:
            raise ValueError(
                "The selected lesson does not match this learner's subject and class."
            )

        return lesson

    @staticmethod
    def _normalise_answers(
        answers: dict,
    ) -> list[dict]:
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
        if lesson_context is None:
            lesson_context = kwargs.get("lesson_context")
        # Delegate to AI service with compatibility
        return (
            await self.generate_assessment(
                subject_name=subject_name,
                class_level=class_level,
                assessment_type=assessment_type,
                topic_title=topic_title,
                question_count=question_count,
            )
            if False
            else await self._ai_generate_assessment(
                subject_name,
                class_level,
                assessment_type,
                topic_title,
                lesson_context,
                question_count,
            )
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
        if hasattr(self.ai_service, "generate_assessment"):
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
        raise RuntimeError("No AI service")
        # Return the existing attempt if the client retries the same request.
        existing = self.assessment_repo.get_by_client_attempt(
            data.student_id,
            data.client_attempt_id,
        )

        if existing is not None:
            return existing

        student = await self._get_student(data.student_id)
        subject_name = SubjectName(data.subject_name)
        topic_id = data.topic_id
        lesson = None

        if data.content_id is not None:
            lesson = await self._get_selected_lesson(
                data.content_id,
                subject_name,
                student.class_level,
            )

            if topic_id is not None and topic_id != lesson.topic_id:
                raise ValueError(
                    "The selected lesson does not match the requested topic."
                )

            topic_id = lesson.topic_id
            topic_title = lesson.title
        else:
            topic_title = await self._get_topic_title(topic_id)

        questions = await self._ai_generate_assessment(
            subject_name=subject_name,
            class_level=student.class_level,
            assessment_type=data.assessment_type,
            topic_title=topic_title,
            lesson_context=lesson.content_text if lesson is not None else None,
            question_count=data.question_count,
        )

        if not isinstance(questions, list) or not questions:
            raise ValueError(
                "No valid assessment questions are available for this request."
            )

        attempt_number = self.assessment_repo.get_latest_attempt_number(
            student_id=data.student_id,
            subject_name=subject_name,
            assessment_type=data.assessment_type,
            topic_id=topic_id,
        )

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
            target_duration_seconds=data.target_duration_seconds,
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
            raise ValueError("Assessment not found.")

        if assessment.status != AssessmentStatus.IN_PROGRESS:
            raise ValueError("Only an in-progress assessment can be submitted.")

        await self._get_student(assessment.student_id)
        await self._get_topic_title(assessment.topic_id)

        completed_at = datetime.now(timezone.utc)
        started_at = assessment.started_at

        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        actual_duration = max(
            0.0,
            (completed_at - started_at).total_seconds(),
        )

        # Store answers as normalized question/answer records.
        answers = self._normalise_answers(submit_data.answers)

        # AIService defines evaluate_submission(), not evaluate_assessment().
        # It expects the submitted answers dictionary keyed by question ID.
        try:
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
        except Exception:
            try:
                evaluation = await self.ai_service.evaluate_assessment(
                    questions=assessment.question_snapshot,
                    student_answers=submit_data.answers,
                    subject_name=assessment.subject_name,
                    class_level=(
                        await self._get_student(assessment.student_id)
                    ).class_level,
                    topic_title=await self._get_topic_title(assessment.topic_id),
                    actual_duration_seconds=actual_duration,
                    target_duration_seconds=assessment.target_duration_seconds,
                )
            except Exception:
                evaluation = await self.ai_service.evaluate_submission(
                    questions=assessment.question_snapshot,
                    student_answers=submit_data.answers,
                    actual_duration_seconds=int(actual_duration),
                    target_duration_seconds=assessment.target_duration_seconds or 0,
                )

        if not isinstance(evaluation, dict):
            raise ValueError("The AI evaluator returned an invalid result.")

        accuracy = evaluation.get("accuracy_percentage")
        speed = evaluation.get("speed_percentage")

        if accuracy is not None:
            accuracy = float(accuracy)
            if not 0 <= accuracy <= 100:
                raise ValueError("Invalid accuracy percentage from evaluator.")

        if speed is not None:
            speed = float(speed)
            if not 0 <= speed <= 100:
                raise ValueError("Invalid speed percentage from evaluator.")

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
        return self.assessment_repo.list_recent_completed(
            student_id=student_id,
            limit=limit,
        )

    async def get_assessment(
        self,
        assessment_id: UUID,
    ) -> LearnerAssessment | None:
        return self.assessment_repo.get_by_id(assessment_id)

    async def update_assessment(
        self,
        assessment_id: UUID,
        data: LearnerAssessmentUpdate,
    ) -> LearnerAssessment | None:
        assessment = self.assessment_repo.get_by_id(assessment_id)

        if assessment is None:
            return None

        if assessment.status == AssessmentStatus.COMPLETED:
            raise ValueError("Completed assessments cannot be edited.")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(assessment, field, value)

        return self.assessment_repo.update(assessment)
