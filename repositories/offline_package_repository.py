from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.enums import ClassLevel, PackageStatus, SubjectName
from models.offline_package import OfflinePackage


class OfflinePackageRepository:
    """Database access only. No business rules and no commits here."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, package_id: UUID) -> OfflinePackage | None:
        return self.db.get(OfflinePackage, package_id)

    def find_duplicate(
        self,
        subject_name: SubjectName,
        class_level: ClassLevel,
        title: str,
        package_version: str,
        exclude_id: UUID | None = None,
    ) -> OfflinePackage | None:
        stmt = select(OfflinePackage).where(
            OfflinePackage.subject_name == subject_name,
            OfflinePackage.class_level == class_level,
            OfflinePackage.title == title,
            OfflinePackage.package_version == package_version,
        )
        if exclude_id is not None:
            stmt = stmt.where(OfflinePackage.package_id != exclude_id)
        return self.db.scalars(stmt.limit(1)).first()

    def list(
        self,
        *,
        subject_name: SubjectName | None = None,
        class_level: ClassLevel | None = None,
        status: PackageStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[OfflinePackage]:
        stmt = select(OfflinePackage)
        if subject_name is not None:
            stmt = stmt.where(OfflinePackage.subject_name == subject_name)
        if class_level is not None:
            stmt = stmt.where(OfflinePackage.class_level == class_level)
        if status is not None:
            stmt = stmt.where(OfflinePackage.status == status)
        stmt = (
            stmt.order_by(OfflinePackage.created_at.desc()).limit(limit).offset(offset)
        )
        return list(self.db.scalars(stmt).all())

    def create(self, values: dict[str, Any]) -> OfflinePackage:
        package = OfflinePackage(**values)
        self.db.add(package)
        self.db.flush()
        self.db.refresh(package)
        return package

    def update(self, package: OfflinePackage, values: dict[str, Any]) -> OfflinePackage:
        for field, value in values.items():
            setattr(package, field, value)
        self.db.flush()
        self.db.refresh(package)
        return package
