import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from google import genai
from google.genai import types
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.enums import ContentType
from database import engine
from models import LearningContent, Topic


CURRICULUM_ROOT = PROJECT_ROOT / "curriculum"
STORE_CONFIG = PROJECT_ROOT / "data" / "gemini_file_search_store.json"


def load_store_name() -> str:
    """Load the existing Gemini File Search Store name."""
    if not STORE_CONFIG.exists():
        raise RuntimeError(f"Store configuration not found: {STORE_CONFIG}")

    config = json.loads(STORE_CONFIG.read_text(encoding="utf-8"))
    name = config.get("name")

    if not name:
        raise RuntimeError("Store configuration does not contain a store name.")

    return name


def find_lesson_file(source_path: str) -> Path:
    """Resolve a lesson path and ensure it is inside the curriculum."""
    path = (PROJECT_ROOT / source_path).resolve()

    if not path.is_relative_to(CURRICULUM_ROOT.resolve()):
        raise ValueError(f"Lesson path is outside curriculum: {source_path}")

    if not path.is_file() or path.name != "lesson.md":
        raise FileNotFoundError(f"Lesson Markdown file not found: {path}")

    return path


def get_existing_source_paths(
    client,
    store_name: str,
) -> set[str]:
    """Find source paths already uploaded to the File Search Store."""
    existing = set()

    documents = client.file_search_stores.documents.list(parent=store_name)

    for document in documents:
        metadata_items = getattr(document, "custom_metadata", None) or []

        for item in metadata_items:
            if getattr(item, "key", None) == "source_path":
                value = getattr(item, "string_value", None)

                if value:
                    existing.add(value)

    return existing


def wait_for_upload(
    client,
    operation,
    timeout_seconds: int = 300,
) -> str:
    """Wait for Gemini to finish processing an uploaded lesson."""
    deadline = time.monotonic() + timeout_seconds

    while not operation.done:
        if time.monotonic() >= deadline:
            raise TimeoutError(
                "Upload processing timed out. Check the File Search "
                "Store before retrying this lesson."
            )

        time.sleep(2)
        operation = client.operations.get(operation)

    if operation.error:
        raise RuntimeError(f"Gemini upload failed: {operation.error}")

    response = operation.response
    document_name = getattr(response, "document_name", None) if response else None

    if not document_name:
        raise RuntimeError(
            "Upload finished without returning a document name. "
            "Check the store before retrying."
        )

    return document_name


def main():
    parser = argparse.ArgumentParser(
        description=("Import Redu Markdown lessons into Gemini File Search.")
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=("Upload lessons and save their document references in PostgreSQL."),
    )
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Check your .env file.")

    store_name = load_store_name()
    client = genai.Client(api_key=api_key)

    try:
        existing_source_paths = get_existing_source_paths(
            client,
            store_name,
        )
    finally:
        client.close()

    print(f"Store: {store_name}")
    print(
        "Documents already in store:",
        len(existing_source_paths),
    )

    with Session(engine) as db:
        rows = db.execute(
            select(LearningContent, Topic)
            .join(
                Topic,
                LearningContent.topic_id == Topic.topic_id,
            )
            .where(LearningContent.content_type == ContentType.LESSON)
            .order_by(
                Topic.class_level,
                Topic.subject_name,
                Topic.title,
            )
        ).all()

        lessons = []

        for content, topic in rows:
            content_data = content.content_data or {}
            source_path = content_data.get("source_path")

            if not source_path:
                raise ValueError(f"Missing source_path for lesson {content.content_id}")

            lesson_path = find_lesson_file(source_path)
            metadata_path = lesson_path.parent / "metadata.json"

            if not metadata_path.is_file():
                raise FileNotFoundError(f"Metadata file missing: {metadata_path}")

            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

            if content.gemini_file_ref:
                print(f"SKIP (database reference exists): {source_path}")
                continue

            if source_path in existing_source_paths:
                print(f"SKIP (already in Gemini store): {source_path}")
                continue

            lessons.append(
                {
                    "content": content,
                    "topic": topic,
                    "path": lesson_path,
                    "metadata": metadata,
                    "source_path": source_path,
                }
            )

        print(f"Lessons to process: {len(lessons)}")
        print(f"Mode: {'UPLOAD' if args.apply else 'PREVIEW ONLY'}")

        for lesson in lessons:
            content = lesson["content"]
            topic = lesson["topic"]

            print(
                f"- {lesson['source_path']} | "
                f"{topic.subject_name.value} | "
                f"{topic.class_level.value} | "
                f"{content.title}"
            )

        if not args.apply:
            print("\nPreview only. No uploads or database changes made.")
            print("Review the list before running with --apply.")
            return

        if not lessons:
            print("\nNothing to upload.")
            return

        client = genai.Client(api_key=api_key)
        imported = 0

        try:
            for lesson in lessons:
                content = lesson["content"]
                topic = lesson["topic"]
                metadata = lesson["metadata"]
                source_path = lesson["source_path"]

                print(
                    f"\nUploading: {source_path}",
                    flush=True,
                )

                operation = client.file_search_stores.upload_to_file_search_store(
                    file_search_store_name=store_name,
                    file=lesson["path"],
                    config=types.UploadToFileSearchStoreConfig(
                        display_name=str(metadata.get("title") or content.title),
                        mime_type="text/markdown",
                        custom_metadata=[
                            types.CustomMetadata(
                                key="source_path",
                                string_value=source_path,
                            ),
                            types.CustomMetadata(
                                key="subject",
                                string_value=(topic.subject_name.value),
                            ),
                            types.CustomMetadata(
                                key="class_level",
                                string_value=(topic.class_level.value),
                            ),
                            types.CustomMetadata(
                                key="content_id",
                                string_value=str(content.content_id),
                            ),
                        ],
                    ),
                )

                document_name = wait_for_upload(
                    client,
                    operation,
                )
                content.gemini_file_ref = document_name
                content.gemini_file_uploaded_at = datetime.now(timezone.utc)
                db.commit()

                imported += 1

                print(
                    f"Imported successfully: {document_name}",
                    flush=True,
                )

        except Exception:
            db.rollback()
            raise
        finally:
            client.close()

        print(f"\nImport finished. Successful uploads: {imported}")


if __name__ == "__main__":
    main()
