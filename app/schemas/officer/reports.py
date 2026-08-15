from pydantic import BaseModel


class SectorScoreRead(BaseModel):
    icon: str
    label: str
    enterprise_count: int
    average_score: int


class ForecastAccuracyRead(BaseModel):
    predicted_vs_actual_label: str
    flags_that_came_true: int
    flags_raised: int
    false_alarms: int


class AppAdoptionRead(BaseModel):
    enterprises_with_streak: int
    total_enterprises: int
    voice_entry_users: int
    active_savings_plans: int


class ReportSummaryRead(BaseModel):
    month_label: str
    compared_to_label: str
    average_health_score: int
    average_health_score_delta: int
    flags_resolved: int
    flags_opened: int
    average_resolution_days: int
    # None (N/A) when the officer has zero assigned enterprises — there's
    # nothing to report an EMI-timeliness rate about.
    emis_on_time_percent: int | None
    emis_on_time_delta: int | None
    visits_done: int
    risk_led_visits: int
    sector_scores: list[SectorScoreRead]
    insight: str
    forecast_accuracy: ForecastAccuracyRead
    app_adoption: AppAdoptionRead
