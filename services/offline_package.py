from uuid import UUID

from core.enums import ClassLevel, PackageStatus, SubjectName
from core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from models.offline_package import OfflinePackage
from repositories.offline_package_repository import OfflinePackageRepository
from schemas.offline_package import OfflinePackageCreate, OfflinePackageUpdate

ALLOWED_TRANSITIONS: dict[PackageStatus, set[PackageStatus]] = {
    PackageStatus.DRAFT: {PackageStatus.PUBLISHED, PackageStatus.WITHDRAWN},
    PackageStatus.PUBLISHED: {PackageStatus.WITHDRAWN},
    PackageStatus.WITHDRAWN: set(),
}


class OfflinePackageService:
    def __init__(self, repo: OfflinePackageRepository) -> None:

        self.repo = repo

    def get_package(self, package_id: UUID) -> OfflinePackage:
        package = self.repo.get(package_id)
        if package is None:
            raise NotFoundError("Offline package not found")
        return package

    def list_packages(
        self,
        *,
        subject_name: SubjectName | None,
        class_level: ClassLevel | None,
        status: PackageStatus | None,
        limit: int,
        offset: int,
    ) -> list[OfflinePackage]:
        return self.repo.list(
            subject_name=subject_name,
            class_level=class_level,
            status=status,
            limit=limit,
            offset=offset,
        )

    def create_package(self, payload: OfflinePackageCreate) -> OfflinePackage:
        values = payload.model_dump(mode="json")
        values["checksum"] = values["checksum"].lower()

        if self.repo.find_duplicate(
            payload.subject_name,
            payload.class_level,
            payload.title,
            payload.package_version,
        ):
            raise ConflictError("A package with this title and version already exists")

        return self.repo.create({**values, "status": PackageStatus.DRAFT})

    def update_package(
        self, package_id: UUID, payload: OfflinePackageUpdate
    ) -> OfflinePackage:
        package = self.get_package(package_id)
        if package.status != PackageStatus.DRAFT:
            raise BusinessRuleError(
                "Only draft packages can be edited. Create a new version instead."
            )

        values = payload.model_dump(mode="json", exclude_unset=True)
        if "checksum" in values and values["checksum"] is not None:
            values["checksum"] = values["checksum"].lower()

        values = {k: v for k, v in values.items() if v is not None}

        new_title = values.get("title", package.title)
        new_version = values.get("package_version", package.package_version)
        if self.repo.find_duplicate(
            package.subject_name,
            package.class_level,
            new_title,
            new_version,
            exclude_id=package.package_id,
        ):
            raise ConflictError("A package with this title and version already exists")

        return self.repo.update(package, values)

    def publish(self, package_id: UUID) -> OfflinePackage:
        package = self.get_package(package_id)
        if not package.manifest:
            raise BusinessRuleError("Cannot publish a package with an empty manifest")
        return self._change_status(package, PackageStatus.PUBLISHED)

    def withdraw(self, package_id: UUID) -> OfflinePackage:
        package = self.get_package(package_id)
        return self._change_status(package, PackageStatus.WITHDRAWN)

    def _change_status(
        self, package: OfflinePackage, new_status: PackageStatus
    ) -> OfflinePackage:
        if new_status not in ALLOWED_TRANSITIONS[package.status]:
            raise BusinessRuleError(
                f"Cannot move a package from '{package.status.value}' to '{new_status.value}'"
            )
        return self.repo.update(package, {"status": new_status})
