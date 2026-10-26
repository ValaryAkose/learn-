import asyncio
from types import SimpleNamespace
from uuid import uuid4

from core.enums import AssessmentType, ClassLevel, ContentType, SubjectName
from schemas.learner_assessment import LearnerAssessmentCreate
from routers.learner_assessment import router as learner_assessment_router
from services.learner_assessment import LearnerAssessmentService


class AssessmentRepository:
    def __init__(self):
        self.db = object()
        self.created = None

    def get_by_client_attempt(self, student_id, client_attempt_id):
        return None

    def get_latest_attempt_number(self, **kwargs):
        return 1

    def create(self, assessment):
        self.created = assessment
        return assessment


class ProgressRepository:
    pass


def test_start_assessment_uses_the_selected_lesson_as_question_scope(monkeypatch):
    student_id = uuid4()
    content_id = uuid4()
    topic_id = uuid4()
    calls = []
    lesson = SimpleNamespace(
        content_id=content_id,
        topic_id=topic_id,
        title="Nutrition in plants",
        content_text="Green plants make food through photosynthesis.",
        content_type=ContentType.LESSON,
    )

    class AI:
        async def generate_assessment(self, **kwargs):
            calls.append(kwargs)
            return [
                {
                    "question_id": "q1",
                    "question_type": "short_answer",
                    "question_text": "How do green plants make food?",
                    "options": [],
                    "correct_answer": "Photosynthesis",
                    "rubric_criteria": [],
                    "points": 1,
                }
            ]

    assessment_repo = AssessmentRepository()
    service = LearnerAssessmentService(assessment_repo, ProgressRepository(), AI())

    async def get_student(requested_student_id):
        assert requested_student_id == student_id
        return SimpleNamespace(class_level=ClassLevel.S1)

    async def get_selected_lesson(requested_content_id, subject_name, class_level):
        assert requested_content_id == content_id
        assert subject_name == SubjectName.BIOLOGY
        assert class_level == ClassLevel.S1
        return lesson

    monkeypatch.setattr(service, "_get_student", get_student)
    monkeypatch.setattr(service, "_get_selected_lesson", get_selected_lesson)
    request = LearnerAssessmentCreate(
        student_id=student_id,
        subject_name=SubjectName.BIOLOGY,
        assessment_type=AssessmentType.PRACTICE,
        content_id=content_id,
        question_count=1,
    )

    assessment = asyncio.run(service.start_assessment(request))

    assert calls[0]["topic_title"] == lesson.title
    assert calls[0]["lesson_context"] == lesson.content_text
    assert assessment.topic_id == topic_id
    assert assessment.question_snapshot[0]["source_lesson"] == {
        "content_id": str(content_id),
        "title": lesson.title,
    }


def test_list_available_lessons_returns_selectable_content_records():

    content_id = uuid4()
    topic_id = uuid4()
    lesson = SimpleNamespace(
        content_id=content_id,
        title="Nutrition in plants",
        simple_definition="How plants make food",
    )
    topic = SimpleNamespace(
        topic_id=topic_id,
        subject_name=SubjectName.BIOLOGY,
        class_level=ClassLevel.S1,
    )

    class Result:
        def all(self):
            return [(lesson, topic)]

    class Database:
        def execute(self, statement):
            return Result()

    service = LearnerAssessmentService(SimpleNamespace(db=Database()))
    options = asyncio.run(
        service.list_available_lessons(SubjectName.BIOLOGY, ClassLevel.S1)
    )

    assert len(options) == 1
    assert options[0].content_id == content_id
    assert options[0].topic_id == topic_id
    assert options[0].title == lesson.title


def test_assessment_router_does_not_expose_delete():
    delete_routes = [
        route for route in learner_assessment_router.routes if "DELETE" in route.methods
    ]

    assert delete_routes == []
