
from pydantic import BaseModel, Field

from app.models.user import Language
from app.schemas.common import ORMModel


class UserRead(ORMModel):
    id: int
    phone_e164: str
    name: str | None
    language: Language
    state: str | None
    district: str | None
    village: str | None
    savings_inr: int
    loan_inr: int
    notifications_enabled: bool


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    language: Language | None = None
    state: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    village: str | None = Field(default=None, max_length=120)
    notifications_enabled: bool | None = None


class SavingsLoanUpdate(BaseModel):
    savings_inr: int = Field(ge=0)
    loan_inr: int = Field(ge=0)


class SessionResponse(BaseModel):
    me: UserRead
    is_new: bool
