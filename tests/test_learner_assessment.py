import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from core.enums import AssessmentStatus, AssessmentType, ClassLevel, SubjectName
from schemas.learner_assessment import LearnerAssessmentCreate, LearnerAssessmentSubmit
from services.learner_assessment import LearnerAssessmentService

_QUESTION = {
    "question_id": "q1",
    "question_type": "short_answer",
    "question_text": "What is photosynthesis?",
    "options": [],
    "correct_answer": "The process by which green plants make food using sunlight.",
    "rubric_criteria": [],
    "points": 1,
}


def _make_assessment(**overrides):
    defaults = dict(
        assessment_id=uuid4(),
        student_id=uuid4(),
        topic_id=uuid4(),
        client_attempt_id=uuid4(),
        assessment_type=AssessmentType.PRACTICE,
        assessment_version=1,
        attempt_number=1,
        subject_name=SubjectName.BIOLOGY,
        status=AssessmentStatus.IN_PROGRESS,
        question_snapshot=[dict(_QUESTION)],
        answers=[],
        identified_gaps=None,
        recommendations=[],
        target_duration_seconds=300,
        actual_duration_seconds=None,
        accuracy_percentage=None,
        speed_percentage=None,
        started_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        client_submitted_at=None,
        completed_at=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class _AssessmentRepo:
    db = None

    def __init__(self, existing=None):
        self._store = {}
        self._created = None
        if existing is not None:
            self._store[existing.assessment_id] = existing

    def get_by_client_attempt(self, student_id, client_attempt_id):
        return None

    def get_latest_attempt_number(self, **kwargs):
        return 1

    def create(self, assessment):
        self._store[assessment.assessment_id] = assessment
        self._created = assessment
        return assessment

    def get_by_id(self, assessment_id):
        return self._store.get(assessment_id)

    def update(self, assessment):
        self._store[assessment.assessment_id] = assessment
        return assessment


class _ProgressRepo:
    def __init__(self):
        self._store = {}

    def get_or_create(self, *, student_id, topic_id, subject_name):
        from core.enums import ProgressStatus

        key = (student_id, topic_id)
        if key not in self._store:
            self._store[key] = SimpleNamespace(
                student_id=student_id,
                topic_id=topic_id,
                subject_name=subject_name,
                progress_status=ProgressStatus.NOT_STARTED,
                last_activity_at=None,
                recommendation_reason=None,
            )
        return self._store[key]

    def update(self, progress):
        return progress


class _AI:
    async def generate_assessment(self, **kwargs):
        return [dict(_QUESTION)]

    async def evaluate_assessment(self, **kwargs):
        return {
            "accuracy_percentage": 100.0,
            "speed_percentage": 80.0,
            "actual_duration_seconds": kwargs.get("actual_duration_seconds"),
            "target_duration_seconds": kwargs.get("target_duration_seconds"),
            "identified_gaps": ["None identified"],
            "recommendations": [{"text": "Keep practising!"}],
            "corrections": [
                {
                    "question_id": "q1",
                    "is_correct": True,
                    "status": "correct",
                    "explanation": "Good answer.",
                    "correct_answer": _QUESTION["correct_answer"],
                }
            ],
        }


def _make_service(assessment=None, ai=None):
    repo = _AssessmentRepo(existing=assessment)
    service = LearnerAssessmentService(repo, _ProgressRepo(), ai or _AI())
    return service, repo


def _patch_service(service, class_level=ClassLevel.S1, topic_title=None):
    async def fake_get_student(sid):
        return SimpleNamespace(class_level=class_level)

    async def fake_get_topic_title(tid):
        return topic_title

    service._get_student = fake_get_student
    service._get_topic_title = fake_get_topic_title


def test_submit_assessment_saves_evaluation_results():
    assessment = _make_assessment()
    service, repo = _make_service(assessment=assessment)
    _patch_service(service, topic_title="Nutrition in plants")

    result = asyncio.run(
        service.submit_assessment(
            assessment.assessment_id,
            LearnerAssessmentSubmit(answers={"q1": "Photosynthesis"}),
        )
    )

    assert result.status == AssessmentStatus.COMPLETED
    assert result.accuracy_percentage == 100.0
    assert result.speed_percentage == 80.0
    assert result.actual_duration_seconds is not None
    assert result.actual_duration_seconds >= 0.0
    assert result.completed_at is not None
    assert result.answers == [{"question_id": "q1", "answer": "Photosynthesis"}]
    assert result.identified_gaps == "None identified"
    assert result.recommendations == [{"text": "Keep practising!"}]


def test_submit_assessment_rejects_already_completed():
    assessment = _make_assessment(status=AssessmentStatus.COMPLETED)
    service, _ = _make_service(assessment=assessment)

    with pytest.raises(ValueError, match="in-progress"):
        asyncio.run(
            service.submit_assessment(
                assessment.assessment_id,
                LearnerAssessmentSubmit(answers={"q1": "Photosynthesis"}),
            )
        )


def test_submit_assessment_raises_for_missing_assessment():
    service, _ = _make_service()

    with pytest.raises(ValueError, match="Assessment not found"):
        asyncio.run(
            service.submit_assessment(
                uuid4(),
                LearnerAssessmentSubmit(answers={"q1": "Photosynthesis"}),
            )
        )


def test_submit_normalises_plain_answer_values():
    assessment = _make_assessment()
    service, _ = _make_service(assessment=assessment)
    _patch_service(service)

    result = asyncio.run(
        service.submit_assessment(
            assessment.assessment_id,
            LearnerAssessmentSubmit(answers={"q1": "Simple string answer"}),
        )
    )

    assert result.answers[0]["question_id"] == "q1"
    assert result.answers[0]["answer"] == "Simple string answer"


def test_submit_normalises_dict_answer_values():
    assessment = _make_assessment()
    service, _ = _make_service(assessment=assessment)
    _patch_service(service)

    result = asyncio.run(
        service.submit_assessment(
            assessment.assessment_id,
            LearnerAssessmentSubmit(
                answers={"q1": {"answer": "dict answer", "time_spent": 45}}
            ),
        )
    )

    assert result.answers[0]["question_id"] == "q1"
    assert result.answers[0]["answer"] == "dict answer"
    assert result.answers[0]["time_spent"] == 45


def test_submit_skips_speed_when_no_target_duration():
    assessment = _make_assessment(target_duration_seconds=None)

    class _AINoSpeed:
        async def evaluate_assessment(self, **kwargs):
            return {
                "accuracy_percentage": 50.0,
                "speed_percentage": None,
                "identified_gaps": [],
                "recommendations": [],
                "corrections": [],
            }

    service, _ = _make_service(assessment=assessment, ai=_AINoSpeed())
    _patch_service(service)

    result = asyncio.run(
        service.submit_assessment(
            assessment.assessment_id,
            LearnerAssessmentSubmit(answers={"q1": "answer"}),
        )
    )

    assert result.speed_percentage is None


def test_start_assessment_returns_existing_when_client_attempt_id_matches():
    student_id = uuid4()
    client_attempt_id = uuid4()
    existing = _make_assessment(
        student_id=student_id, client_attempt_id=client_attempt_id
    )

    class _IdempotentRepo(_AssessmentRepo):
        def get_by_client_attempt(self, sid, cid):
            if sid == student_id and cid == client_attempt_id:
                return existing
            return None

    repo = _IdempotentRepo()
    service = LearnerAssessmentService(repo, _ProgressRepo(), _AI())

    result = asyncio.run(
        service.start_assessment(
            LearnerAssessmentCreate(
                student_id=student_id,
                subject_name=SubjectName.BIOLOGY,
                assessment_type=AssessmentType.PRACTICE,
                client_attempt_id=client_attempt_id,
            )
        )
    )

    assert result is existing
    assert repo._created is None


def test_assessment_router_has_start_and_submit_routes():
    from routers.learner_assessment import router

    paths = {route.path for route in router.routes}
    assert "/assessments/start" in paths
    assert "/assessments/{assessment_id}/submit" in paths


def test_assessment_router_has_no_delete_routes():
    from routers.learner_assessment import router

    delete_routes = [
        route
        for route in router.routes
        if hasattr(route, "methods") and "DELETE" in route.methods
    ]
    assert delete_routes == []


def test_assessment_router_start_requires_post():
    from routers.learner_assessment import router

    start_routes = [r for r in router.routes if r.path == "/assessments/start"]
    assert len(start_routes) == 1
    assert "POST" in start_routes[0].methods


def test_assessment_router_submit_requires_post():
    from routers.learner_assessment import router

    submit_routes = [
        r for r in router.routes if r.path == "/assessments/{assessment_id}/submit"
    ]
    assert len(submit_routes) == 1
    assert "POST" in submit_routes[0].methods


def test_submit_schema_rejects_empty_answers():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        LearnerAssessmentSubmit(answers={})


def test_create_schema_defaults_question_count_to_three():
    schema = LearnerAssessmentCreate(
        student_id=uuid4(),
        subject_name=SubjectName.BIOLOGY,
        assessment_type=AssessmentType.PRACTICE,
    )
    assert schema.question_count == 3


def test_create_schema_rejects_zero_question_count():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        LearnerAssessmentCreate(
            student_id=uuid4(),
            subject_name=SubjectName.BIOLOGY,
            assessment_type=AssessmentType.PRACTICE,
            question_count=0,
        )
