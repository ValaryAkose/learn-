import os
from uuid import UUID

from dotenv import load_dotenv

load_dotenv()


def get_required_uuid(name: str) -> UUID:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set in the environment")
    return UUID(value)


def get_uuid_set(name: str) -> frozenset[UUID]:
    raw = os.getenv(name, "")
    return frozenset(UUID(item.strip()) for item in raw.split(",") if item.strip())


DEFAULT_GENERAL_TOPIC_ID = get_required_uuid("DEFAULT_GENERAL_TOPIC_ID")
PLACEHOLDER_TOPIC_IDS = get_uuid_set("PLACEHOLDER_TOPIC_IDS")
