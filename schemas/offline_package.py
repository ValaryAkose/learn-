from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import AnyUrl, BaseModel, ConfigDict, Field

from core.enums import ClassLevel, PackageStatus, SubjectName

SHA256_PATTERN = r"^[A-Fa-f0-9]{64}$"


class OfflinePackageBase(BaseModel):
    subject_name: SubjectName
    class_level: ClassLevel
    title: str = Field(..., min_length=1, max_length=150)
    package_version: str = Field(..., min_length=1, max_length=20)
    manifest: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Ordered content IDs/versions and required asset paths.",
    )
    manifest_uri: str
    size_bytes: int = Field(
        ..., ge=0, description="Download size estimate. Must be non-negative."
    )
    file_path_url: str = Field(..., min_length=1, max_length=255)
    checksum: str = Field(
        ..., pattern=SHA256_PATTERN, description="SHA-256 hash of the bundle."
    )


class OfflinePackageCreate(OfflinePackageBase):
    manifest_uri: AnyUrl


class OfflinePackageUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    package_version: Optional[str] = Field(default=None, min_length=1, max_length=20)
    manifest: Optional[List[Dict[str, Any]]] = None
    manifest_uri: Optional[AnyUrl] = None
    size_bytes: Optional[int] = Field(default=None, ge=0)
    file_path_url: Optional[str] = Field(default=None, min_length=1, max_length=255)
    checksum: Optional[str] = Field(default=None, pattern=SHA256_PATTERN)


class OfflinePackageResponse(OfflinePackageBase):
    model_config = ConfigDict(from_attributes=True)

    package_id: UUID
    status: PackageStatus
    created_at: datetime
