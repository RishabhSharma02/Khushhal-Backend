from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.officer_security import get_current_officer
from app.db.session import get_db
from app.models.officer import Officer
from app.schemas.officer.reports import ReportSummaryRead
from app.services.officer import reports_service

router = APIRouter(prefix="/reports", tags=["officer-reports"])


@router.get("", response_model=ReportSummaryRead)
async def get_reports(
    db: AsyncSession = Depends(get_db),
    current: Officer = Depends(get_current_officer),
) -> ReportSummaryRead:
    return await reports_service.get_reports(db, current.id)
