"""Officer auth: verify a Firebase ID token (email/password) and resolve it
against `officers`.

Deliberately self-contained rather than reusing app.core.security's
`_identity_from_request` — that helper hard-requires a `phone_number` claim
(the consumer app signs in via Firebase Phone OTP), which an email/password
token never carries. Keeping this logic here means app/core/security.py
never has to change to accommodate officers.

Two identity resolvers are exposed:
  - `get_current_officer` — sign-in. 403s if no `officers` row matches the
    token's uid; used by every officer endpoint except registration.
  - `get_verified_officer_identity` — token verification only, no lookup.
    Used by POST /auth/register, where no `officers` row exists yet.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.officer import Officer
from app.repositories.officer import officers as officers_repo

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
        import json

        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(json.loads(settings.firebase_credentials_json))
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        log.info("firebase_admin_initialized")
        return True
    except ValueError:
        # Already initialized by app.core.security in this process — fine,
        # both modules just want a usable default app.
        _firebase_initialized = True
        return True
    except Exception as exc:
        log.error("firebase_admin_init_failed", err=str(exc))
        return False


@dataclass(slots=True)
class OfficerFirebaseIdentity:
    uid: str
    email: str | None


async def _verify_officer_id_token(token: str) -> OfficerFirebaseIdentity:
    from firebase_admin import auth as fb_auth

    def _verify() -> dict[str, Any]:
        return fb_auth.verify_id_token(token, check_revoked=False)

    try:
        decoded = await asyncio.to_thread(_verify)
    except Exception as exc:
        log.info("officer_firebase_verify_failed", err=str(exc))
        raise UnauthorizedError("Invalid or expired token") from exc

    uid = decoded.get("uid") or decoded.get("user_id")
    if not uid:
        raise UnauthorizedError("Token missing uid")
    return OfficerFirebaseIdentity(uid=uid, email=decoded.get("email"))


def _unverified_decode(token: str) -> OfficerFirebaseIdentity:
    """Base64-decode the JWT payload without signature verification. Used
    ONLY as a dev fallback when the server has no Firebase Admin credentials
    configured — see DEV_TOOLS_ENABLED handling below. Never call this in
    production.
    """
    import base64
    import json

    parts = token.split(".")
    if len(parts) < 2:
        raise UnauthorizedError("Malformed bearer token")
    padded = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except Exception as e:
        raise UnauthorizedError("Cannot decode token payload") from e

    uid = payload.get("user_id") or payload.get("sub") or payload.get("uid")
    if not uid:
        raise UnauthorizedError("Token missing uid")
    return OfficerFirebaseIdentity(uid=uid, email=payload.get("email"))


async def _officer_identity_from_request(
    request: Request,
    settings: Settings,
    x_debug_firebase_uid: str | None,
    x_debug_email: str | None,
) -> OfficerFirebaseIdentity:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        if _init_firebase(settings):
            return await _verify_officer_id_token(token)
        if settings.dev_tools_enabled:
            log.warning("officer_dev_trust_decoding_bearer_no_admin_creds")
            return _unverified_decode(token)
        raise UnauthorizedError("Firebase not configured on server")

    if settings.dev_tools_enabled and x_debug_firebase_uid:
        return OfficerFirebaseIdentity(uid=x_debug_firebase_uid, email=x_debug_email)

    raise UnauthorizedError("Missing bearer token")


async def get_verified_officer_identity(
    request: Request,
    settings: Settings = Depends(get_settings),
    x_debug_firebase_uid: str | None = Header(default=None, alias="X-Debug-Firebase-Uid"),
    x_debug_email: str | None = Header(default=None, alias="X-Debug-Email"),
) -> OfficerFirebaseIdentity:
    """Verifies the token/dev-shim only — no `officers` lookup. Used by
    registration, where the officer row doesn't exist yet.
    """
    return await _officer_identity_from_request(request, settings, x_debug_firebase_uid, x_debug_email)


async def get_current_officer(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_debug_firebase_uid: str | None = Header(default=None, alias="X-Debug-Firebase-Uid"),
    x_debug_email: str | None = Header(default=None, alias="X-Debug-Email"),
) -> Officer:
    identity = await _officer_identity_from_request(request, settings, x_debug_firebase_uid, x_debug_email)
    officer = await officers_repo.get_by_firebase_uid(db, identity.uid)
    if officer is None:
        raise ForbiddenError("No officer account is registered for this sign-in")
    return officer
