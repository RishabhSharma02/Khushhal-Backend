"""Firebase Admin auth: verify ID tokens and expose get_current_user dependency.

In dev, when Settings.dev_tools_enabled=true and no Firebase credentials are
configured, the dependency also honors an `X-Debug-Firebase-Uid` header so the
backend can be exercised before Flutter has Firebase wired.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import UnauthorizedError
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.user import User

log = get_logger(__name__)

_firebase_initialized = False


def _init_firebase(settings: Settings) -> bool:
    """Idempotently initialize firebase_admin. Returns True if usable."""
    global _firebase_initialized
    if _firebase_initialized:
        return True
    if not settings.firebase_credentials_json:
        return False
    try:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(json.loads(settings.firebase_credentials_json))
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        log.info("firebase_admin_initialized")
        return True
    except Exception as exc:
        log.error("firebase_admin_init_failed", err=str(exc))
        return False


@dataclass(slots=True)
class FirebaseIdentity:
    uid: str
    phone_e164: str


async def _verify_id_token(token: str) -> FirebaseIdentity:
    from firebase_admin import auth as fb_auth

    def _verify() -> dict[str, Any]:
        return fb_auth.verify_id_token(token, check_revoked=False)

    try:
        decoded = await asyncio.to_thread(_verify)
    except Exception as exc:
        log.info("firebase_verify_failed", err=str(exc))
        raise UnauthorizedError("Invalid or expired token") from exc

    uid = decoded.get("uid") or decoded.get("user_id")
    phone = decoded.get("phone_number")
    if not uid or not phone:
        raise UnauthorizedError("Token missing uid or phone_number")
    return FirebaseIdentity(uid=uid, phone_e164=phone)


async def _identity_from_request(
    request: Request,
    settings: Settings,
    x_debug_firebase_uid: str | None,
    x_debug_phone: str | None,
) -> FirebaseIdentity:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        if not _init_firebase(settings):
            raise UnauthorizedError("Firebase not configured on server")
        return await _verify_id_token(token)

    if settings.dev_tools_enabled and x_debug_firebase_uid:
        phone = x_debug_phone or f"+91{int(hash(x_debug_firebase_uid)) % 10_000_000_000:010d}"
        return FirebaseIdentity(uid=x_debug_firebase_uid, phone_e164=phone)

    raise UnauthorizedError("Missing bearer token")


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_debug_firebase_uid: str | None = Header(default=None, alias="X-Debug-Firebase-Uid"),
    x_debug_phone: str | None = Header(default=None, alias="X-Debug-Phone"),
) -> User:
    from app.services.auth_service import find_or_create_user_from_firebase

    identity = await _identity_from_request(request, settings, x_debug_firebase_uid, x_debug_phone)
    return await find_or_create_user_from_firebase(db, identity.uid, identity.phone_e164)
