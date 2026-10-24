import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
from collections import defaultdict

from sqlalchemy import select

from core.enums import ClassLevel, ContentType, SubjectName
from models import LearningContent, Topic

try:
    from services.content_parser_service import discover_lessons, parse_lesson  # type: ignore
except Exception:
    from pathlib import Path

    def discover_lessons() -> list[Path]:
        root = Path(__file__).resolve().parent.parent / "curriculum"
        pattern = "**/lesson.md"
        return list(root.glob(pattern)) if root.exists() else []

    def parse_lesson(path: Path) -> dict:

        parts = path.parts
        try:
            idx = parts.index("curriculum")
            class_level = parts[idx + 1]
            subject = parts[idx + 2]
        except Exception:
            class_level = "S1"
            subject = "Unknown"

        title = path.parent.name
        try:
            content_text = path.read_text(encoding="utf-8")
        except Exception:
            content_text = ""

        return {
            "class_level": class_level,
            "subject": subject,
            "title": title,
            "content_text": content_text,
            "source_path": str(path),
            "metadata_path": None,
            "images_folder": None,
            "metadata": {},
            "review_required": False,
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preview or import S1/S2 curriculum lessons."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write lessons to PostgreSQL. Without this flag, only preview.",
    )
    args = parser.parse_args()

    lesson_paths = discover_lessons()
    lessons = []
    for path in lesson_paths:
        lessons.append(parse_lesson(path))

    print(f"Found {len(lessons)} valid lessons.")
    for lesson in lessons:
        print(
            f"  {lesson['class_level']} | {lesson['subject']} | "
            f"{lesson['title']} | {lesson['source_path']}"
        )

    if not args.apply:
        print("\nPreview only. Nothing was written to the database.")
        print("Review the list, then run with --apply to import.")
        return
    from database import SessionLocal

    session = SessionLocal()
    imported = 0
    skipped = 0
    sequence_numbers: dict[tuple[str, str], int] = defaultdict(int)

    try:
        for lesson in lessons:
            source_path = lesson["source_path"]

            existing_content = session.scalar(
                select(LearningContent).where(
                    LearningContent.content_data["source_path"].astext == source_path
                )
            )
            if existing_content is not None:
                skipped += 1
                continue

            subject = lesson["subject"]
            class_level = lesson["class_level"]

            try:
                subject_name = SubjectName(subject.lower())
            except ValueError:
                subject_name = SubjectName(subject.lower().replace(" ", "_"))

            try:
                class_name = ClassLevel(class_level.upper())
            except ValueError:
                class_name = ClassLevel(class_level)

            topic = session.scalar(
                select(Topic).where(
                    Topic.subject_name == subject_name,
                    Topic.class_level == class_name,
                    Topic.title == lesson["title"],
                )
            )

            if topic is None:
                group = (class_name.value, subject_name.value)
                sequence_numbers[group] += 1

                topic = Topic(
                    subject_name=subject_name,
                    class_level=class_name,
                    title=lesson["title"],
                    sequence_no=sequence_numbers[group],
                    description=(f"Imported from {source_path}"),
                )
                session.add(topic)
                session.flush()

            content_data = {
                "source_path": source_path,
                "metadata_path": lesson["metadata_path"],
                "images_folder": lesson["images_folder"],
                "metadata": lesson["metadata"],
                "review_required": lesson["review_required"],
            }

            content = LearningContent(
                topic_id=topic.topic_id,
                content_type=ContentType.LESSON,
                title=lesson["title"],
                content_text=lesson["content_text"],
                content_data=content_data,
            )
            session.add(content)
            imported += 1

        session.commit()
        print("\nImport completed successfully.")
        print(f"Lessons imported: {imported}")
        print(f"Existing lessons skipped: {skipped}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
