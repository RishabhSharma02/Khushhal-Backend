from pydantic import BaseModel


class DashboardRead(BaseModel):
    average_score_history: list[int]
    average_score_delta: int
    emis_on_time_percent: int
    emis_on_time_delta: int
    open_flag_count: int
    open_flag_delta: int
    visits_done_this_week: int
    visits_planned_this_week: int
