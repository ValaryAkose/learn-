import argparse
import os
import sys
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

from sqlalchemy import select

from core.enums import ClassLevel, ContentType, SubjectName
from database import get_session_factory
from models import LearningContent, Topic


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


def discover_files() -> list[Path]:
    source_dir = PROJECT_ROOT / required_env("DICTIONARY_SEED_DIR")
    pattern = required_env("DICTIONARY_SEED_GLOB")
    return sorted(source_dir.glob(pattern)) if source_dir.exists() else []


def apply_seed(files: list[Path]) -> None:
    subject = SubjectName[required_env("DICTIONARY_SEED_SUBJECT")]
    class_level = ClassLevel[required_env("DICTIONARY_SEED_CLASS_LEVEL")]
    topic_title = required_env("DICTIONARY_SEED_TOPIC_TITLE")

    session_factory = get_session_factory()
    with session_factory() as session:
        topic = (
            session.execute(
                select(Topic).where(
                    Topic.subject_name == subject,
                    Topic.class_level == class_level,
                    Topic.title == topic_title,
                )
            )
            .scalars()
            .first()
        )

        if topic is None:
            topic = Topic(
                subject_name=subject,
                class_level=class_level,
                title=topic_title,
                sequence_no=0,
                description="Learner dictionary entries",
            )
            session.add(topic)
            session.flush()

        imported = 0
        updated = 0

        for path in files:
            text = path.read_text(encoding="utf-8")
            existing = (
                session.execute(
                    select(LearningContent).where(
                        LearningContent.content_type == ContentType.GLOSSARY,
                        LearningContent.title == path.stem,
                    )
                )
                .scalars()
                .first()
            )

            if existing is not None:
                existing.content_text = text
                updated += 1
                continue

            extra = {}
            if hasattr(LearningContent, "content_series_id"):
                extra["content_series_id"] = uuid4()
            if hasattr(LearningContent, "content_data"):
                extra["content_data"] = {"source_path": str(path)}

            session.add(
                LearningContent(
                    topic_id=topic.topic_id,
                    content_type=ContentType.GLOSSARY,
                    title=path.stem,
                    content_text=text,
                    **extra,
                )
            )
            imported += 1

        session.commit()
        print(f"Imported: {imported}")
        print(f"Updated: {updated}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed dictionary markdown files into the database."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write entries to the database. Without this flag, preview only.",
    )
    args = parser.parse_args()

    files = discover_files()
    print(f"Found {len(files)} dictionary files.")
    for path in files:
        print(" -", path.relative_to(PROJECT_ROOT))

    if not files:
        raise SystemExit(1)

    if not args.apply:
        print("\nPreview only. Run with --apply to import into the database.")
        return

    apply_seed(files)


if __name__ == "__main__":
    main()
