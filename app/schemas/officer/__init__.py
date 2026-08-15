from pydantic import Field

from app.schemas.common import ORMModel


class OfficerRead(ORMModel):
    """Consumer-facing view of an officer — enough to render the home card
    and let the owner call/email. Mirrors the fields the app's
    `AssignedOfficer` model reads."""

    id: int
    employee_id: str = Field(max_length=40)
    full_name: str = Field(max_length=120)
    email: str | None = Field(default=None, max_length=160)
    mobile_e164: str | None = Field(default=None, max_length=20)


__all__ = ["OfficerRead"]
