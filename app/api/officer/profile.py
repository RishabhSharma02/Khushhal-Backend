from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.officer_security import get_current_officer
from app.db.session import get_db
from app.models.officer import Officer
from app.schemas.officer.profile import CoverageRead, OfficerRead, OfficerUpdate
from app.services.officer import coverage_service
from app.services.officer.officer_service import update_officer

router = APIRouter(tags=["officer-profile"])


@router.get("/profile", response_model=OfficerRead)
async def get_officer_profile(current: Officer = Depends(get_current_officer)) -> OfficerRead:
    return OfficerRead.model_validate(current)


@router.get("/profile/coverage", response_model=CoverageRead)
async def get_officer_coverage(
    db: AsyncSession = Depends(get_db),
    current: Officer = Depends(get_current_officer),
) -> CoverageRead:
    return await coverage_service.get_coverage(db, current.id)


@router.patch("/profile", response_model=OfficerRead)
async def patch_officer_profile(
    payload: OfficerUpdate,
    db: AsyncSession = Depends(get_db),
    current: Officer = Depends(get_current_officer),
) -> OfficerRead:
    updated = await update_officer(db, current, payload)
    return OfficerRead.model_validate(updated)
