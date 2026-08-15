from datetime import date

from pydantic import BaseModel


class EnterpriseContactRead(BaseModel):
    name: str
    role: str
    phone: str
    language: str
    best_time: str


class EnterpriseFinancialsRead(BaseModel):
    cash_on_hand_inr: int
    month_net_inr: int
    savings_inr: int
    loan_left_inr: int
    emi_inr: int
    emi_on_time: bool


class EnterpriseRead(BaseModel):
    id: str
    name: str
    icon: str
    segment: str
    sector: str
    village: str
    established_year: int
    staff_count: int
    member_since: date
    contact: EnterpriseContactRead
    health_score: int
    score_rising: bool
    risk_level: str
    flag_summary: str | None
    financials: EnterpriseFinancialsRead
    last_sync_hours_ago: int | None
    stale_days: int | None


class CashFlowMonthRead(BaseModel):
    label: str
    money_in_inr: int
    money_out_inr: int
    # The forecast's actual predicted quantity (Forecast.cf_pred) — only set
    # when `is_forecast` is true. `money_in_inr`/`money_out_inr` for
    # forecast months are a synthetic split (out held at the recent
    # average, in derived from it) that isn't a real prediction on its
    # own; `net_inr` is the genuine model output.
    net_inr: int | None = None
    is_forecast: bool
    is_flagged: bool


class DataQualityRead(BaseModel):
    entry_streak_days_per_week: int
    forecast_confidence_percent: int
