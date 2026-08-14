from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.officer_security import get_current_officer
from app.db.session import get_db
from app.models.officer import Officer
from app.schemas.officer.dashboard import DashboardRead
from app.services.officer import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["officer-dashboard"])


@router.get("", response_model=DashboardRead)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current: Officer = Depends(get_current_officer),
) -> DashboardRead:
    return await dashboard_service.get_dashboard(db, current.id)
