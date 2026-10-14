from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    ADMIN = "admin"


class ClassLevel(str, Enum):
    S1 = "S1"
    S2 = "S2"


class SubjectName(str, Enum):
    BIOLOGY = "biology"
    CHEMISTRY = "chemistry"
    PHYSICS = "physics"
    ENGLISH = "english"
    MATHEMATICS = "mathematics"


class ConsentStatus(str, Enum):
    PENDING = "pending"
    GRANTED = "granted"
    WITHDRAWN = "withdrawn"


class ContentType(str, Enum):
    LESSON = "lesson"
    EXAMPLE = "example"
    QUESTION = "question"
    GLOSSARY = "glossary"


class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_ANSWER = "short_answer"
    LONG_ANSWER = "long_answer"


class AssessmentType(str, Enum):
    DIAGNOSTIC = "diagnostic"
    PRACTICE = "practice"
    QUIZ = "quiz"


class AssessmentStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ProgressStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    MASTERED = "mastered"


class EvaluationStatus(str, Enum):
    NEEDS_SUPPORT = "needs_support"
    DEVELOPING = "developing"
    SECURE = "secure"


class TutorType(str, Enum):
    SUBJECT = "subject"
    LANGUAGE = "language"


class ExplanationMode(str, Enum):
    SIMPLE = "simple"
    STANDARD = "standard"
    STEP_BY_STEP = "step_by_step"
    EXAMPLE = "example"


class ResponseStatus(str, Enum):
    ANSWERED = "answered"
    NOT_IN_CURRICULUM = "not_in_curriculum"
    BLOCKED = "blocked"
    ERROR = "error"


class PackageStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"


class SyncEventType(str, Enum):
    PROGRESS_SYNC = "progress_sync"
    PACKAGE_DOWNLOAD = "package_download"


class SyncStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class LessonProgressStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
