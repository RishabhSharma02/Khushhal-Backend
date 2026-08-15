from datetime import datetime

from pydantic import BaseModel, Field

from app.models.visit import VisitRiskLevel


class VisitRead(BaseModel):
    id: int
    enterprise_id: str
    enterprise_name: str
    village: str
    date: datetime
    agenda: str
    status: str
    risk_level: str | None
    distance_km: float | None


class VisitCreate(BaseModel):
    business_id: int
    date: datetime
    agenda: str = Field(min_length=1, max_length=400)
    # Typed as the enum (not str) — see ActionStepCreate's note on why an
    # invalid value must be rejected here, not in the service layer.
    risk_level: VisitRiskLevel | None = None
