import pytest
from fastapi.testclient import TestClient

from models.user import User
from models.topic import Topic
from models.learning_content import LearningContent
from models.learner_assessment import LearnerAssessment
from models.learner_progress import LearnerProgress
from models.learner_lesson_progress import LearnerLessonProgress
from models.ai_tutor_interaction import AITutorInteraction
from models.offline_package import OfflinePackage
from models.sync_event import SyncEvent

MODELS = (
    User,
    Topic,
    LearningContent,
    LearnerAssessment,
    LearnerLessonProgress,
    AITutorInteraction,
    OfflinePackage,
    SyncEvent,
    LearnerProgress,
)


@pytest.fixture(scope="session")
def model_classes():
    """Return all mapped model classes, keyed by their database table name."""
    return {model.__tablename__: model for model in MODELS}


@pytest.fixture(scope="module")
def client():
    from main import app

    with TestClient(app) as test_client:
        yield test_client
