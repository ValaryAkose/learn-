import asyncio
import json
from types import SimpleNamespace

from core.enums import AssessmentType, ClassLevel, SubjectName
from services.ai_service import AIService


def test_generate_assessment_uses_scoped_file_search_and_validates_questions(
    monkeypatch,
):
    service = AIService.__new__(AIService)
    service.store_name = "fileSearchStores/redu-curriculum"
    service.model_name = "gemini-3.8-flash"
    service.api_key = "test-key"
    expected_question = {
        "question_id": "q1",
        "question_type": "multiple_choice",
        "question_text": "Which process do plants use to make food?",
        "options": ["Respiration", "Photosynthesis", "Digestion", "Excretion"],
        "correct_answer": "Photosynthesis",
        "rubric_criteria": [],
        "points": 1,
    }
    calls = []

    async def fake_ask_gemini(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(text=json.dumps({"questions": [expected_question]}))

    monkeypatch.setattr(service, "_ask_gemini", fake_ask_gemini)

    questions = asyncio.run(
        service.generate_assessment(
            subject_name=SubjectName.BIOLOGY,
            class_level=ClassLevel.S1,
            assessment_type=AssessmentType.PRACTICE,
            topic_title="Nutrition in plants",
            lesson_context="Green plants make food through photosynthesis.",
            question_count=2,
        )
    )

    assert questions == [expected_question]
    assert calls[0]["is_json"] is True
    assert calls[0].get("use_file_search", True) is True
    assert "Nutrition in plants" in calls[0]["input"]
    assert "Green plants make food through photosynthesis." in calls[0]["input"]
    assert calls[0]["tools"][0]["metadata_filter"] == (
        'subject="biology" AND class_level="S1"'
    )
    assert "Green plants make food through photosynthesis." in calls[0]["input"]
