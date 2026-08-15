from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.officer_security import get_current_officer
from app.db.session import get_db
from app.models.officer import Officer
from app.schemas.officer.enterprises import CashFlowMonthRead, DataQualityRead, EnterpriseRead
from app.services.officer import enterprise_service

router = APIRouter(prefix="/enterprises", tags=["officer-enterprises"])


@router.get("", response_model=list[EnterpriseRead])
async def list_enterprises(
    db: AsyncSession = Depends(get_db),
    current: Officer = Depends(get_current_officer),
) -> list[EnterpriseRead]:
    return await enterprise_service.list_enterprises(db, current.id)


@router.get("/{business_id}", response_model=EnterpriseRead)
async def get_enterprise(
    business_id: int,
    db: AsyncSession = Depends(get_db),
    current: Officer = Depends(get_current_officer),
) -> EnterpriseRead:
    return await enterprise_service.get_enterprise(db, current.id, business_id)


@router.get("/{business_id}/cash-flow", response_model=list[CashFlowMonthRead])
async def get_cash_flow(
    business_id: int,
    db: AsyncSession = Depends(get_db),
    current: Officer = Depends(get_current_officer),
) -> list[CashFlowMonthRead]:
    return await enterprise_service.get_cash_flow(db, current.id, business_id)


@router.get("/{business_id}/data-quality", response_model=DataQualityRead)
async def get_data_quality(
    business_id: int,
    db: AsyncSession = Depends(get_db),
    current: Officer = Depends(get_current_officer),
) -> DataQualityRead:
    return await enterprise_service.get_data_quality(db, current.id, business_id)
