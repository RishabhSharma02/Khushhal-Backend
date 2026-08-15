
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.business import Business
from app.models.monthly_snapshot import MonthlySnapshot
from app.models.user import User
from app.repositories import businesses as biz_repo
from app.schemas.business import (
    BusinessCreate,
    BusinessRead,
    BusinessUpdate,
    MonthlySnapshotRead,
)
from app.services import business_service


def _to_read(
    biz: Business,
    snap: MonthlySnapshot | None,
    assigned_officer_id: int | None = None,
) -> BusinessRead:
    read = BusinessRead.model_validate(biz)
    updates: dict[str, object] = {}
    if snap is not None:
        updates["latest_snapshot"] = MonthlySnapshotRead.model_validate(snap)
    if read.officer_id is None and assigned_officer_id is not None:
        updates["officer_id"] = assigned_officer_id
    if updates:
        return read.model_copy(update=updates)
    return read


async def _reads_for(db: AsyncSession, items: list[Business]) -> list[BusinessRead]:
    ids = [b.id for b in items]
    snaps = await biz_repo.latest_snapshots_map(db, ids)
    officers = await biz_repo.assigned_officer_ids_map(db, ids)
    return [_to_read(b, snaps.get(b.id), officers.get(b.id)) for b in items]


router = APIRouter(tags=["businesses"], prefix="/businesses")


@router.post("", response_model=BusinessRead, status_code=status.HTTP_201_CREATED)
async def create_business(
    payload: BusinessCreate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> BusinessRead:
    biz = await business_service.create_business(db, current, payload)
    return (await _reads_for(db, [biz]))[0]


@router.get("", response_model=list[BusinessRead])
async def list_businesses(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[BusinessRead]:
    items = await business_service.list_businesses(db, current)
    return await _reads_for(db, items)


@router.get("/{business_id}", response_model=BusinessRead)
async def get_business(
    business_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> BusinessRead:
    biz = await business_service.require_owned(db, business_id, current)
    return (await _reads_for(db, [biz]))[0]


@router.patch("/{business_id}", response_model=BusinessRead)
async def patch_business(
    business_id: int,
    payload: BusinessUpdate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> BusinessRead:
    biz = await business_service.update_business(db, business_id, current, payload)
    return (await _reads_for(db, [biz]))[0]


@router.delete("/{business_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_business(
    business_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    await business_service.soft_delete_business(db, business_id, current)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
