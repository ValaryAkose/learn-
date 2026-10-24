import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from database import Base, get_session_factory
from models.ai_tutor_interaction import AITutorInteraction
from models.learning_content import LearningContent
from models.learner_assessment import LearnerAssessment
from models.learner_lesson_progress import LearnerLessonProgress
from models.learner_progress import LearnerProgress
from models.offline_package import OfflinePackage
from models.sync_event import SyncEvent
from models.topic import Topic
from models.user import User

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


@pytest.fixture(scope="session", autouse=True)
def init_test_schema():
    session_factory = get_session_factory()
    engine = session_factory.kw.get("bind")

    if engine and str(engine.url) == "sqlite://":
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        session_factory.configure(bind=engine)

    if engine:
        Base.metadata.create_all(bind=engine)

    yield


@pytest.fixture(scope="session")
def model_classes():
    return {model.__tablename__: model for model in MODELS}


@pytest.fixture(scope="module")
def client():
    from main import app

    with TestClient(app) as test_client:
        yield test_client
