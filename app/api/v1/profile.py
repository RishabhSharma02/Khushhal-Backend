
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import SavingsLoanUpdate, UserRead

router = APIRouter(tags=["profile"])


@router.patch("/me/savings-loan", response_model=UserRead)
async def patch_savings_loan(
    payload: SavingsLoanUpdate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> UserRead:
    current.savings_inr = payload.savings_inr
    current.loan_inr = payload.loan_inr
    current.updated_by = current.id
    await db.commit()
    await db.refresh(current)
    return UserRead.model_validate(current)
