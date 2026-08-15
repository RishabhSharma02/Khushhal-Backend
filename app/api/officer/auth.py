from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.officer_security import (
    OfficerFirebaseIdentity,
    get_current_officer,
    get_verified_officer_identity,
)
from app.db.session import get_db
from app.models.officer import Officer
from app.schemas.officer.profile import OfficerRead, OfficerRegister, OfficerSessionResponse
from app.services.officer.officer_service import register_officer

router = APIRouter(tags=["officer-auth"])


@router.post("/auth/session", response_model=OfficerSessionResponse)
async def create_officer_session(
    current: Officer = Depends(get_current_officer),
) -> OfficerSessionResponse:
    """Exchange a Firebase ID token (or dev shim headers) for the officer
    profile. Sign-in only — 403s if no officers row matches. Registration
    is a separate step (POST /auth/register) since it collects additional
    fields (employee ID, mobile, ...) a plain sign-in doesn't have.
    """
    return OfficerSessionResponse(officer=OfficerRead.model_validate(current))


@router.post("/auth/register", response_model=OfficerSessionResponse)
async def register(
    payload: OfficerRegister,
    db: AsyncSession = Depends(get_db),
    identity: OfficerFirebaseIdentity = Depends(get_verified_officer_identity),
) -> OfficerSessionResponse:
    """Creates the officers row for a Firebase account the app just created
    via createUserWithEmailAndPassword — the token proves the email/password
    signup succeeded; this call attaches the officer profile fields to it.
    """
    officer = await register_officer(db, identity, payload)
    return OfficerSessionResponse(officer=OfficerRead.model_validate(officer))
