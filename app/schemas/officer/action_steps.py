from pydantic import BaseModel, Field

from app.models.action_step import ActionStepImpact
from app.schemas.common import ORMModel


class ActionStepRead(ORMModel):
    id: int
    ordinal: int
    title: str
    detail: str
    impact: str


class ActionStepCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    detail: str = Field(default="", max_length=400)
    # Typed as the enum (not str) so an invalid value is rejected by
    # FastAPI's request validation (422) instead of reaching the service
    # layer's ActionStepImpact(...) conversion, which raised an uncaught
    # ValueError -> 500.
    impact: ActionStepImpact


class ActionStepUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    detail: str = Field(default="", max_length=400)
    impact: ActionStepImpact
