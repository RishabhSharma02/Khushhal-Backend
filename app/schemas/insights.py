
from datetime import date, datetime

from pydantic import BaseModel

from app.models.health_score import RiskLevel, ScoreBand
from app.models.risk_alert import AlertKind, AlertSeverity, PlanActionRole
from app.schemas.common import ORMModel


class HealthRead(ORMModel):
    id: int
    business_id: int
    as_on: date
    next_update: date
    score: int
    risk: RiskLevel
    delta: int | None
    days_written: int
    days_in_month: int
    band: ScoreBand
    p_green: float
    p_amber: float
    p_red: float
    model_version: str


class ForecastMonthRead(ORMModel):
    horizon: int
    cf_pred: float
    in_level: float
    out_level: float
    is_risk_month: bool


class ForecastRead(BaseModel):
    business_id: int
    as_on: date
    months: list[ForecastMonthRead]


class PlanActionRead(ORMModel):
    id: int
    role: PlanActionRole
    ordinal: int
    label_en: str
    label_hi: str | None
    done: bool
    done_at: datetime | None


class RiskAlertRead(ORMModel):
    id: int
    business_id: int
    as_on: date
    kind: AlertKind
    severity: AlertSeverity
    driver: str
    has_plan: bool
    raised_on: date
    resolved_at: datetime | None


class RiskAlertDetail(RiskAlertRead):
    plan_actions: list[PlanActionRead]


class PlanActionUpdate(BaseModel):
    done: bool
