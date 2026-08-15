from pydantic import BaseModel


class DashboardRead(BaseModel):
    average_score_history: list[int]
    average_score_delta: int
    # None (N/A) when the officer has zero assigned enterprises — there's
    # nothing to report an EMI-timeliness rate about.
    emis_on_time_percent: int | None
    emis_on_time_delta: int | None
    open_flag_count: int
    open_flag_delta: int
    visits_done_this_week: int
    visits_planned_this_week: int
