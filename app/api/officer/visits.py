from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.officer_security import get_current_officer
from app.db.session import get_db
from app.models.officer import Officer
from app.schemas.officer.visits import VisitCreate, VisitRead
from app.services.officer import visit_service

router = APIRouter(prefix="/visits", tags=["officer-visits"])


@router.get("", response_model=list[VisitRead])
async def list_visits(
    db: AsyncSession = Depends(get_db),
    current: Officer = Depends(get_current_officer),
) -> list[VisitRead]:
    return await visit_service.list_visits(db, current)


@router.post("", response_model=VisitRead, status_code=status.HTTP_201_CREATED)
async def create_visit(
    payload: VisitCreate,
    db: AsyncSession = Depends(get_db),
    current: Officer = Depends(get_current_officer),
) -> VisitRead:
    return await visit_service.create_visit(db, current, payload)
