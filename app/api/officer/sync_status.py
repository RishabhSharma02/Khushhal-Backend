from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.officer_security import get_current_officer
from app.db.session import get_db
from app.models.officer import Officer
from app.schemas.officer.sync_status import SyncStatusSummary
from app.services.officer import sync_status_service

router = APIRouter(prefix="/sync-status", tags=["officer-sync-status"])


@router.get("", response_model=SyncStatusSummary)
async def get_sync_status(
    db: AsyncSession = Depends(get_db),
    current: Officer = Depends(get_current_officer),
) -> SyncStatusSummary:
    return await sync_status_service.get_sync_status(db, current.id)
