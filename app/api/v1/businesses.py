
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories import businesses as biz_repo
from app.schemas.business import (
    BusinessCreate,
    BusinessRead,
    BusinessUpdate,
    MonthlySnapshotRead,
)
from app.services import business_service


def _attach_snapshot(biz, snap) -> BusinessRead:
    read = BusinessRead.model_validate(biz)
    if snap is not None:
        read = read.model_copy(update={"latest_snapshot": MonthlySnapshotRead.model_validate(snap)})
    return read

router = APIRouter(tags=["businesses"], prefix="/businesses")


@router.post("", response_model=BusinessRead, status_code=status.HTTP_201_CREATED)
async def create_business(
    payload: BusinessCreate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> BusinessRead:
    biz = await business_service.create_business(db, current, payload)
    snap = await biz_repo.latest_snapshot(db, biz.id)
    return _attach_snapshot(biz, snap)


@router.get("", response_model=list[BusinessRead])
async def list_businesses(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[BusinessRead]:
    items = await business_service.list_businesses(db, current)
    snaps = await biz_repo.latest_snapshots_map(db, [b.id for b in items])
    return [_attach_snapshot(b, snaps.get(b.id)) for b in items]


@router.get("/{business_id}", response_model=BusinessRead)
async def get_business(
    business_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> BusinessRead:
    biz = await business_service.require_owned(db, business_id, current)
    snap = await biz_repo.latest_snapshot(db, biz.id)
    return _attach_snapshot(biz, snap)


@router.patch("/{business_id}", response_model=BusinessRead)
async def patch_business(
    business_id: int,
    payload: BusinessUpdate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> BusinessRead:
    biz = await business_service.update_business(db, business_id, current, payload)
    snap = await biz_repo.latest_snapshot(db, biz.id)
    return _attach_snapshot(biz, snap)


@router.delete("/{business_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_business(
    business_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    await business_service.soft_delete_business(db, business_id, current)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
