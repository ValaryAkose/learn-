"""Structural/unit tests for the Redu SQLAlchemy model modules.

These tests intentionally need no running database. They import the real model
modules and inspect SQLAlchemy's mapped metadata.
"""

from __future__ import annotations

import importlib

import pytest
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID


MODEL_MODULES = {
    "models.user": ("User", "users"),
    "models.topic": ("Topic", "topics"),
    "models.learning_content": ("LearningContent", "learning_content"),
    "models.learner_assessment": ("LearnerAssessment", "learner_assessments"),
    "models.learner_progress": ("LearnerProgress", "learner_progress"),
    "models.learner_lesson_progress": (
        "LearnerLessonProgress",
        "learner_lesson_progress",
    ),
    "models.ai_tutor_interaction": ("AITutorInteraction", "ai_tutor_interactions"),
    "models.offline_package": ("OfflinePackage", "offline_packages"),
    "models.sync_event": ("SyncEvent", "sync_events"),
}

# A model's lifecycle timestamp is not always named created_at. Attempts start,
# topic state updates, and sync events record their own appropriate timestamps.
LIFECYCLE_TIMESTAMPS = {
    "users": "created_at",
    "topics": "created_at",
    "learning_content": "created_at",
    "learner_assessments": "started_at",
    "learner_progress": "updated_at",
    "learner_lesson_progress": "updated_at",
    "ai_tutor_interactions": "created_at",
    "offline_packages": "created_at",
    "sync_events": "received_at",
}


@pytest.fixture(scope="session")
def model_classes():
    """Import every model module and return classes keyed by table name."""
    result = {}
    for module_name, (class_name, table_name) in MODEL_MODULES.items():
        module = importlib.import_module(module_name)
        model = getattr(module, class_name)
        assert model.__tablename__ == table_name
        result[table_name] = model
    return result


def test_models_package_imports():
    """The models package itself should be importable from the project root."""
    importlib.import_module("models")


def test_every_model_module_imports_and_maps_expected_table(model_classes):
    assert set(model_classes) == {table for _, table in MODEL_MODULES.values()}


@pytest.mark.parametrize(
    "module_name,class_name,table_name",
    [(module_name, *model_info) for module_name, model_info in MODEL_MODULES.items()],
)
def test_each_model_has_primary_key(module_name, class_name, table_name, model_classes):
    model = model_classes[table_name]
    primary_key_columns = list(model.__table__.primary_key.columns)
    assert len(primary_key_columns) == 1, (
        f"{table_name} should have one primary-key column"
    )
    assert primary_key_columns[0].primary_key is True


@pytest.mark.parametrize(
    "module_name,class_name,table_name",
    [(module_name, *model_info) for module_name, model_info in MODEL_MODULES.items()],
)
def test_each_model_primary_key_is_postgres_uuid(
    module_name, class_name, table_name, model_classes
):
    model = model_classes[table_name]
    pk = next(iter(model.__table__.primary_key.columns))
    assert isinstance(pk.type, PGUUID)
    assert pk.type.as_uuid is True


@pytest.mark.parametrize(
    "module_name,class_name,table_name",
    [(module_name, *model_info) for module_name, model_info in MODEL_MODULES.items()],
)
def test_each_model_has_required_lifecycle_timestamp(
    module_name, class_name, table_name, model_classes
):
    model = model_classes[table_name]
    timestamp_name = LIFECYCLE_TIMESTAMPS[table_name]
    assert timestamp_name in model.__table__.columns
    col = model.__table__.columns[timestamp_name]
    assert col.nullable is False
    assert col.type.timezone is True
    assert col.server_default is not None


def test_model_foreign_keys_target_existing_tables(model_classes):
    """Catch misspelled/missing table references across the uploaded modules."""
    metadata = next(iter(model_classes.values())).metadata
    known_tables = set(metadata.tables)
    assert known_tables == set(model_classes)

    unresolved = []
    for table in metadata.tables.values():
        for fk in table.foreign_keys:
            if fk.column.table.name not in known_tables:
                unresolved.append(
                    f"{table.name}.{fk.parent.name} -> {fk.target_fullname}"
                )
    assert not unresolved, "Unresolved foreign keys: " + ", ".join(unresolved)


def test_user_account_fields_and_profile_json_types(model_classes):
    table = model_classes["users"].__table__
    required = {
        "user_id",
        "learner_code",
        "display_name",
        "email",
        "password_hash",
        "role",
        "class_level",
        "prior_education_background",
        "learning_goals",
        "device_connectivity",
        "consent_status",
        "created_at",
        "updated_at",
    }
    assert required <= set(table.columns.keys())
    assert isinstance(table.c.user_id.type, PGUUID)
    assert isinstance(table.c.learning_goals.type, JSONB)
    assert isinstance(table.c.device_connectivity.type, JSONB)
    assert table.c.email.unique is True


def test_topic_has_self_reference_and_curriculum_fields(model_classes):
    table = model_classes["topics"].__table__
    assert {
        "topic_id",
        "subject_name",
        "class_level",
        "term",
        "parent_topic_id",
        "title",
        "sequence_no",
    } <= set(table.columns.keys())
    assert isinstance(table.c.parent_topic_id.type, PGUUID)
    assert any(
        fk.target_fullname == "topics.topic_id"
        for fk in table.c.parent_topic_id.foreign_keys
    )


def test_learning_content_has_versioned_content_and_question_fields(model_classes):
    table = model_classes["learning_content"].__table__
    assert {
        "content_id",
        "content_series_id",
        "topic_id",
        "content_type",
        "content_text",
        "question_type",
        "answer_options",
        "correct_answer",
        "version",
    } <= set(table.columns.keys())
    assert isinstance(table.c.answer_options.type, JSONB)
    assert isinstance(table.c.content_data.type, JSONB)
    assert table.c.version.nullable is False
    assert table.c.topic_id.nullable is False


def test_assessment_attempt_has_idempotency_and_answer_snapshots(model_classes):
    table = model_classes["learner_assessments"].__table__
    assert {
        "assessment_id",
        "student_id",
        "client_attempt_id",
        "question_snapshot",
        "answers",
        "recommendations",
        "status",
    } <= set(table.columns.keys())
    assert isinstance(table.c.question_snapshot.type, JSONB)
    assert isinstance(table.c.answers.type, JSONB)
    assert table.c.client_attempt_id.nullable is False
    constraints = [
        c
        for c in table.constraints
        if getattr(c, "name", None) == "uq_assessment_student_client_attempt"
    ]
    assert len(constraints) == 1


def test_learner_progress_is_unique_per_student_topic(model_classes):
    table = model_classes["learner_progress"].__table__
    assert {
        "student_id",
        "topic_id",
        "progress_status",
        "recommended_content_id",
    } <= set(table.columns.keys())
    unique_pairs = {
        tuple(col.name for col in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("student_id", "topic_id") in unique_pairs


def test_lesson_progress_is_unique_per_student_content(model_classes):
    table = model_classes["learner_lesson_progress"].__table__
    assert {"student_id", "topic_id", "content_id", "status", "completed_at"} <= set(
        table.columns.keys()
    )
    unique_pairs = {
        tuple(col.name for col in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("student_id", "content_id") in unique_pairs


def test_tutor_interaction_has_grounding_and_offline_fields(model_classes):
    table = model_classes["ai_tutor_interactions"].__table__
    assert {
        "student_id",
        "conversation_id",
        "topic_id",
        "content_id",
        "student_query",
        "ai_response",
        "is_saved_offline",
    } <= set(table.columns.keys())
    assert table.c.student_query.nullable is False
    assert table.c.ai_response.nullable is False
    assert table.c.is_saved_offline.nullable is False


def test_offline_package_has_manifest_and_nonnegative_size_constraint(model_classes):
    table = model_classes["offline_packages"].__table__
    assert {
        "package_id",
        "subject_name",
        "class_level",
        "package_version",
        "manifest",
        "manifest_uri",
        "size_bytes",
        "checksum",
    } <= set(table.columns.keys())
    assert isinstance(table.c.manifest.type, JSONB)
    assert table.c.size_bytes.nullable is False
    checks = [c for c in table.constraints if c.__class__.__name__ == "CheckConstraint"]
    assert any("size_bytes >= 0" in str(c.sqltext) for c in checks)


def test_sync_event_has_retry_safety_device_and_package_reference(model_classes):
    table = model_classes["sync_events"].__table__
    assert {
        "sync_id",
        "client_event_id",
        "student_id",
        "device_id",
        "event_type",
        "package_id",
        "event_payload",
    } <= set(table.columns.keys())
    assert isinstance(table.c.event_payload.type, JSONB)
    unique_pairs = {
        tuple(col.name for col in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("student_id", "client_event_id") in unique_pairs


def test_sqlalchemy_enum_columns_use_python_enums(model_classes):
    enum_columns = []
    for table in next(iter(model_classes.values())).metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, SQLEnum):
                enum_columns.append((table.name, col.name, col.type))
    assert enum_columns, "Expected SQLAlchemy Enum columns in the model set"
    for table_name, col_name, sql_enum in enum_columns:
        assert sql_enum.enum_class is not None, (
            f"{table_name}.{col_name} has no Python enum class"
        )
        assert list(sql_enum.enum_class), f"{table_name}.{col_name} enum has no members"


def test_python_defaults_are_callable_or_literal(model_classes):
    """UUID and collection defaults should be Python defaults, not shared mutable values."""
    for table in next(iter(model_classes.values())).metadata.tables.values():
        for col in table.columns:
            if (
                col.default is not None
                and col.name.endswith("_id")
                and isinstance(col.type, PGUUID)
            ):
                assert callable(col.default.arg), (
                    f"{table.name}.{col.name} should have a callable UUID default"
                )
            if col.default is not None and isinstance(col.type, JSONB):
                assert callable(col.default.arg), (
                    f"{table.name}.{col.name} should use a factory for JSON defaults"
                )


# Additional table/column contract tests. These use SQLAlchemy's mapped metadata
# and require no running PostgreSQL server.
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)


def test_assessment_topic_subject_is_one_composite_foreign_key(model_classes):
    table = model_classes["learner_assessments"].__table__
    matches = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        and tuple(column.name for column in constraint.columns)
        == ("topic_id", "subject_name")
    ]
    assert len(matches) == 1
    assert tuple(element.target_fullname for element in matches[0].elements) == (
        "topics.topic_id",
        "topics.subject_name",
    )


def test_progress_topic_subject_is_one_composite_foreign_key(model_classes):
    table = model_classes["learner_progress"].__table__
    matches = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        and tuple(column.name for column in constraint.columns)
        == ("topic_id", "subject_name")
    ]
    assert len(matches) == 1
    assert tuple(element.target_fullname for element in matches[0].elements) == (
        "topics.topic_id",
        "topics.subject_name",
    )


def test_topics_has_unique_target_for_composite_foreign_keys(model_classes):
    table = model_classes["topics"].__table__
    unique_pairs = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("topic_id", "subject_name") in unique_pairs


COLUMN_CONTRACT_CASES = [
    
    ("users", "user_id", PGUUID, False),
    ("users", "learner_code", String, True),
    ("users", "display_name", String, False),
    ("users", "email", String, True),
    ("users", "password_hash", String, True),
    ("users", "role", SQLEnum, False),
    ("users", "school_name", String, True),
    ("users", "class_level", SQLEnum, True),
    ("users", "class_name", String, True),
    ("users", "prior_education_background", Text, True),
    ("users", "learning_goals", JSONB, True),
    ("users", "device_connectivity", JSONB, True),
    ("users", "consent_status", SQLEnum, False),
    ("users", "updated_at", DateTime, False),
    # topics — 9 (23 cumulative)
    ("topics", "topic_id", PGUUID, False),
    ("topics", "subject_name", SQLEnum, False),
    ("topics", "class_level", SQLEnum, False),
    ("topics", "term", Integer, True),
    ("topics", "parent_topic_id", PGUUID, True),
    ("topics", "title", String, False),
    ("topics", "sequence_no", Integer, False),
    ("topics", "is_active", Boolean, False),
    ("topics", "created_at", DateTime, False),
    

    ("learning_content", "content_id", PGUUID, False),
    ("learning_content", "content_series_id", PGUUID, False),
    ("learning_content", "topic_id", PGUUID, False),
    ("learning_content", "content_type", SQLEnum, False),
    ("learning_content", "title", String, True),
    ("learning_content", "content_text", Text, False),
    ("learning_content", "media_url", String, True),
    ("learning_content", "gemini_file_ref", String, True),
    ("learning_content", "question_type", SQLEnum, True),
    ("learning_content", "answer_options", JSONB, True),
    ("learning_content", "correct_answer", Text, True),
    ("learning_content", "worked_solution", Text, True),
    ("learning_content", "content_data", JSONB, True),
    ("learning_content", "version", Integer, False),
    ("learning_content", "gemini_file_uploaded_at", DateTime, True),
    ("learning_content", "created_at", DateTime, False),
    ("learning_content", "updated_at", DateTime, False),


    ("learner_assessments", "assessment_id", PGUUID, False),
    ("learner_assessments", "student_id", PGUUID, False),
    ("learner_assessments", "topic_id", PGUUID, True),
    ("learner_assessments", "client_attempt_id", PGUUID, False),
    ("learner_assessments", "assessment_type", SQLEnum, False),
    ("learner_assessments", "assessment_version", Integer, False),
    ("learner_assessments", "attempt_number", Integer, False),
    ("learner_assessments", "subject_name", SQLEnum, False),
    ("learner_assessments", "status", SQLEnum, False),
    ("learner_assessments", "question_snapshot", JSONB, False),
    ("learner_assessments", "answers", JSONB, False),
    ("learner_assessments", "identified_gaps", Text, True),
    ("learner_assessments", "recommendations", JSONB, False),
    ("learner_assessments", "started_at", DateTime, False),


    
    ("learner_progress", "progress_id", PGUUID, False),
    ("learner_progress", "student_id", PGUUID, False),
    ("learner_progress", "subject_name", SQLEnum, False),
    ("learner_progress", "topic_id", PGUUID, False),
    ("learner_progress", "progress_status", SQLEnum, False),
    ("learner_progress", "recommendation_reason", Text, True),
    ("learner_progress", "latest_evaluation", SQLEnum, True),
    ("learner_progress", "recommended_content_id", PGUUID, True),
    ("learner_progress", "first_activity_at", DateTime, True),
    ("learner_progress", "updated_at", DateTime, False),



    ("learner_lesson_progress", "lesson_progress_id", PGUUID, False),
    ("learner_lesson_progress", "student_id", PGUUID, False),
    ("learner_lesson_progress", "topic_id", PGUUID, False),
    ("learner_lesson_progress", "content_id", PGUUID, False),
    ("learner_lesson_progress", "status", SQLEnum, False),
    ("learner_lesson_progress", "completed_at", DateTime, True),
    ("learner_lesson_progress", "updated_at", DateTime, False),



    ("ai_tutor_interactions", "interaction_id", PGUUID, False),
    ("ai_tutor_interactions", "conversation_id", PGUUID, False),
    ("ai_tutor_interactions", "student_id", PGUUID, False),
    ("ai_tutor_interactions", "content_id", PGUUID, True),
    ("ai_tutor_interactions", "tutor_type", SQLEnum, False),
    ("ai_tutor_interactions", "student_query", Text, False),
    ("ai_tutor_interactions", "explanation_mode", SQLEnum, False),
    ("ai_tutor_interactions", "ai_response", Text, False),
    ("ai_tutor_interactions", "model_name", String, False),
    ("ai_tutor_interactions", "response_status", SQLEnum, False),
    ("ai_tutor_interactions", "is_saved_offline", Boolean, False),
    ("ai_tutor_interactions", "created_at", DateTime, False),



    ("offline_packages", "package_id", PGUUID, False),
    ("offline_packages", "subject_name", SQLEnum, False),
    ("offline_packages", "class_level", SQLEnum, False),
    ("offline_packages", "title", String, False),
    ("offline_packages", "package_version", String, False),
    ("offline_packages", "manifest", JSONB, False),
    ("offline_packages", "size_bytes", Integer, False),
    ("offline_packages", "checksum", String, False),
    ("offline_packages", "status", SQLEnum, False),
    ("offline_packages", "created_at", DateTime, False),



    ("sync_events", "sync_id", PGUUID, False),
    ("sync_events", "client_event_id", PGUUID, False),
    ("sync_events", "student_id", PGUUID, False),
    ("sync_events", "device_id", PGUUID, False),
    ("sync_events", "event_type", SQLEnum, False),
    ("sync_events", "sync_status", SQLEnum, False),
    ("sync_events", "records_synced", Integer, False),
    ("sync_events", "package_id", PGUUID, True),
    ("sync_events", "package_version", String, True),
    ("sync_events", "event_payload", JSONB, True),
    ("sync_events", "error_code", String, True),
    ("sync_events", "received_at", DateTime, False),
    ("sync_events", "processed_at", DateTime, True),
]

assert len(COLUMN_CONTRACT_CASES) == 106


@pytest.mark.parametrize(
    "table_name,column_name,expected_type,expected_nullable",
    COLUMN_CONTRACT_CASES,
)
def test_model_column_type_and_nullability(
    table_name, column_name, expected_type, expected_nullable, model_classes
):
    table = model_classes[table_name].__table__
    assert column_name in table.columns, f"Missing column {table_name}.{column_name}"
    column = table.columns[column_name]
    assert isinstance(column.type, expected_type), (
        f"{table_name}.{column_name}: expected {expected_type.__name__}, "
        f"got {type(column.type).__name__}"
    )
    assert column.nullable is expected_nullable, (
        f"{table_name}.{column_name}: expected nullable={expected_nullable}, "
        f"got nullable={column.nullable}"
    )
