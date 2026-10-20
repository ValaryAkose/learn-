from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import ClassLevel, PackageStatus, SubjectName
from database import Base


class OfflinePackage(Base):
    __tablename__ = "offline_packages"

    __table_args__ = (
        CheckConstraint(
            "size_bytes >= 0",
            name="ck_offline_package_size_non_negative",
        ),
    )

    package_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    subject_name: Mapped[SubjectName] = mapped_column(
        SQLEnum(SubjectName, name="subject_name"),
        nullable=False,
    )

    class_level: Mapped[ClassLevel] = mapped_column(
        SQLEnum(ClassLevel, name="class_level"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    package_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    manifest: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    manifest_uri: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    file_path_url: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    checksum: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    status: Mapped[PackageStatus] = mapped_column(
        SQLEnum(PackageStatus, name="package_status"),
        nullable=False,
        default=PackageStatus.DRAFT,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
