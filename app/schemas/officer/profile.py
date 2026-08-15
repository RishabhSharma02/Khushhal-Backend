from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class OfficerRead(ORMModel):
    id: int
    employee_id: str
    employee_id_verified: bool
    full_name: str
    mobile_e164: str | None
    email: str | None
    pincode: str | None
    block: str | None
    state: str | None
    device_label: str | None


class OfficerUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    mobile_e164: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=160)
    pincode: str | None = Field(default=None, max_length=10)
    block: str | None = Field(default=None, max_length=80)
    state: str | None = Field(default=None, max_length=80)
    device_label: str | None = Field(default=None, max_length=120)


class OfficerSessionResponse(BaseModel):
    officer: OfficerRead


class CoverageRead(BaseModel):
    """The Profile screen's "My coverage" tile — aggregated server-side
    across the officer's assigned enterprises, not part of OfficerRead
    since it's only needed when the profile screen is actually open.
    """

    enterprise_count: int
    village_count: int
    visits_this_month: int
    flags_resolved_last_30_days: int


class OfficerRegister(BaseModel):
    employee_id: str = Field(min_length=1, max_length=40)
    full_name: str = Field(min_length=1, max_length=120)
    # Not needed for auth (that's email/password) — contact-only, so
    # optional at signup; can be added later via profile edit.
    mobile_e164: str | None = Field(default=None, max_length=20)
    pincode: str | None = Field(default=None, max_length=10)
    block: str | None = Field(default=None, max_length=80)
    state: str | None = Field(default=None, max_length=80)
