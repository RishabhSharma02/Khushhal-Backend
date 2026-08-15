from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories import officers as officer_repo
from app.schemas.officer import OfficerRead

router = APIRouter(tags=["officers"], prefix="/officers")


@router.get("/{officer_id}", response_model=OfficerRead)
async def get_officer(
    officer_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> OfficerRead:
    officer = await officer_repo.get(db, officer_id)
    if officer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="officer_not_found")
    return OfficerRead.model_validate(officer)
