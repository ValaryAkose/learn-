#!/usr/bin/env python3
import os
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.user import User
from models.topic import Topic
from models.learner_progress import LearnerProgress
from core.enums import UserRole, ClassLevel, SubjectName, ProgressStatus

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/redu"
)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def seed():
    db = SessionLocal()
    try:
        # Create a test user (student)
        student_id = uuid.uuid4()
        user = User(
            user_id=student_id,
            learner_code="STU001",
            display_name="Test Student",
            first_name="Test",
            last_name="Student",
            email="student@test.com",
            role=UserRole.STUDENT,
            class_level=ClassLevel.S1,
            consent_status="granted",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created user: {user.user_id} ({user.email})")

        # Get existing topics or create one
        topics = db.query(Topic).all()
        if not topics:
            topic = Topic(
                topic_id=uuid.uuid4(),
                subject_name=SubjectName.MATHEMATICS,
                class_level=ClassLevel.S1,
                title="Algebra Basics",
                topic_slug="algebra-basics",
                description="Introduction to algebra",
            )
            db.add(topic)
            db.commit()
            db.refresh(topic)
            topics = [topic]
            print(f"Created topic: {topic.topic_id} ({topic.title})")
        else:
            print(f"Found {len(topics)} topics:")
            for t in topics:
                print(f"  - {t.topic_id} | {t.subject_name} | {t.title}")

        # Create learner progress for first topic
        topic = topics[0]
        progress = LearnerProgress(
            progress_id=uuid.uuid4(),
            student_id=student_id,
            topic_id=topic.topic_id,
            subject_name=topic.subject_name,
            progress_status=ProgressStatus.NOT_STARTED,
            completion_percentage=0,
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)
        print(f"Created learner progress: {progress.progress_id}")
        print(f"  student_id: {progress.student_id}")
        print(f"  topic_id: {progress.topic_id}")
        print(f"  subject_name: {progress.subject_name}")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
