
from datetime import date

from pydantic import BaseModel, Field

from app.models.business import BusinessSector, BusinessSegment, BusinessTenure
from app.models.monthly_snapshot import MoneyBasis
from app.schemas.common import ORMModel


class MonthlyMoneyIn(BaseModel):
    money_in: int = Field(ge=0)
    money_out: int = Field(ge=0)
    loan_emi: int = Field(ge=0)
    savings: int = Field(ge=0)
    basis: MoneyBasis


class BusinessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    segment: BusinessSegment
    sector: BusinessSector
    tenure: BusinessTenure
    staff_count: int = Field(ge=1)
    is_new_business: bool = False
    years_in_operation: int = Field(default=0, ge=0)
    monthly: MonthlyMoneyIn | None = None


class BusinessUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    segment: BusinessSegment | None = None
    sector: BusinessSector | None = None
    tenure: BusinessTenure | None = None
    staff_count: int | None = Field(default=None, ge=1)
    is_new_business: bool | None = None
    years_in_operation: int | None = Field(default=None, ge=0)


class MonthlySnapshotRead(ORMModel):
    id: int
    business_id: int
    month: date
    money_in: int
    money_out: int
    loan_emi: int
    savings: int
    basis: MoneyBasis


class BusinessRead(ORMModel):
    id: int
    name: str
    segment: BusinessSegment
    sector: BusinessSector
    tenure: BusinessTenure
    staff_count: int
    is_new_business: bool
    years_in_operation: int
    # The most recent monthly baseline captured for this business — usually
    # the setup-wizard row. Present so the client can seed Home's money
    # tiles from the onboarding numbers before any live ledger entries land.
    latest_snapshot: MonthlySnapshotRead | None = None
