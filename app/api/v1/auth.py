
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.core.security import _identity_from_request
from app.db.session import get_db
from app.schemas.user import SessionResponse, UserRead
from app.services.auth_service import find_or_create_returning_flag

router = APIRouter(tags=["auth"])


@router.post("/auth/session", response_model=SessionResponse)
@limiter.limit("10/minute")
async def create_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_debug_firebase_uid: str | None = Header(default=None, alias="X-Debug-Firebase-Uid"),
    x_debug_phone: str | None = Header(default=None, alias="X-Debug-Phone"),
) -> SessionResponse:
    """Exchange a Firebase ID token (or dev shim headers) for the app user.

    Flutter calls this immediately after `signInWithCredential`. Returns the
    user profile and whether this was a first-time sign-in so the app can
    route to onboarding vs the home shell.
    """
    identity = await _identity_from_request(request, settings, x_debug_firebase_uid, x_debug_phone)
    user, is_new = await find_or_create_returning_flag(db, identity.uid, identity.phone_e164)
    return SessionResponse(me=UserRead.model_validate(user), is_new=is_new)


@router.post("/auth/ping")
async def ping() -> dict:
    return {"ok": True}
