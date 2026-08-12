
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_me(current: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current)


@router.patch("/me", response_model=UserRead)
async def patch_me(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> UserRead:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current, field, value)
    current.updated_by = current.id
    await db.commit()
    await db.refresh(current)
    return UserRead.model_validate(current)
