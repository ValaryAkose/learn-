from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.enums import SyncEventType, SyncStatus


class SyncEventBase(BaseModel):
    client_event_id: UUID
    student_id: UUID
    device_id: UUID
    event_type: SyncEventType
    sync_status: SyncStatus
    records_synced: int = Field(default=0, ge=0)
    package_id: Optional[UUID] = None
    package_version: Optional[str] = Field(default=None, max_length=20)
    event_payload: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = Field(default=None, max_length=50)
    client_occurred_at: Optional[datetime] = None


class SyncEventCreate(SyncEventBase):
    @model_validator(mode="after")
    def check_event_shape(self) -> "SyncEventCreate":
        if self.event_type == SyncEventType.PACKAGE_DOWNLOAD:
            if self.package_id is None:
                raise ValueError("package_id is required for package_download events")
            if self.records_synced != 0:
                raise ValueError("records_synced must be 0 for package_download events")
            if self.event_payload:
                raise ValueError(
                    "event_payload must be empty for package_download events"
                )
        elif self.package_id is not None or self.package_version is not None:
            raise ValueError(
                "package fields are only allowed on package_download events"
            )
        return self


class SyncEventResponse(SyncEventBase):
    model_config = ConfigDict(from_attributes=True)

    sync_id: UUID
    received_at: datetime
    processed_at: Optional[datetime] = None
