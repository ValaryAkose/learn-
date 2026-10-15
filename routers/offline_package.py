from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.enums import ClassLevel, PackageStatus, SubjectName
from database import get_db
from repositories.offline_package_repository import OfflinePackageRepository
from schemas.offline_package import (
    OfflinePackageCreate,
    OfflinePackageResponse,
    OfflinePackageUpdate,
)
from services.offline_package import OfflinePackageService

router = APIRouter(prefix="/offline-packages", tags=["offline packages"])


def get_service(db: Session = Depends(get_db)) -> OfflinePackageService:
    repo = OfflinePackageRepository(db)
    return OfflinePackageService(repo)


@router.post(
    "", response_model=OfflinePackageResponse, status_code=status.HTTP_201_CREATED
)
def create_package(
    payload: OfflinePackageCreate,
    db: Session = Depends(get_db),
    service: OfflinePackageService = Depends(get_service),
):
    package = service.create_package(payload)
    db.commit()
    return package


@router.get("", response_model=list[OfflinePackageResponse])
def list_packages(
    subject_name: SubjectName | None = None,
    class_level: ClassLevel | None = None,
    package_status: PackageStatus | None = Query(
        default=PackageStatus.PUBLISHED, alias="status"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: OfflinePackageService = Depends(get_service),
):
    return service.list_packages(
        subject_name=subject_name,
        class_level=class_level,
        status=package_status,
        limit=limit,
        offset=offset,
    )


@router.get("/{package_id}", response_model=OfflinePackageResponse)
def get_package(
    package_id: UUID, service: OfflinePackageService = Depends(get_service)
):
    return service.get_package(package_id)


@router.patch("/{package_id}", response_model=OfflinePackageResponse)
def update_package(
    package_id: UUID,
    payload: OfflinePackageUpdate,
    db: Session = Depends(get_db),
    service: OfflinePackageService = Depends(get_service),
):
    package = service.update_package(package_id, payload)
    db.commit()
    return package


@router.post("/{package_id}/publish", response_model=OfflinePackageResponse)
def publish_package(
    package_id: UUID,
    db: Session = Depends(get_db),
    service: OfflinePackageService = Depends(get_service),
):
    package = service.publish(package_id)
    db.commit()
    return package


@router.post("/{package_id}/withdraw", response_model=OfflinePackageResponse)
def withdraw_package(
    package_id: UUID,
    db: Session = Depends(get_db),
    service: OfflinePackageService = Depends(get_service),
):
    package = service.withdraw(package_id)
    db.commit()
    return package
