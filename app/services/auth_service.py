
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import RowStatus
from app.models.user import User
from app.repositories import users as users_repo


async def find_or_create_user_from_firebase(
    db: AsyncSession, firebase_uid: str, phone_e164: str
) -> User:
    user, _ = await find_or_create_returning_flag(db, firebase_uid, phone_e164)
    return user


async def _get_by_phone_any_status(db: AsyncSession, phone_e164: str) -> User | None:
    """Find a user row for this phone regardless of soft-delete state.

    The UNIQUE constraint on `phone_e164` fires against every row in the
    table, not just non-deleted ones — so a re-signup on the same phone
    number after a soft-delete would 409 without this lookup.
    """
    stmt = select(User).where(User.phone_e164 == phone_e164)
    return (await db.execute(stmt)).scalar_one_or_none()


async def find_or_create_returning_flag(
    db: AsyncSession, firebase_uid: str, phone_e164: str
) -> tuple[User, bool]:
    existing = await users_repo.get_by_firebase_uid(db, firebase_uid)
    if existing is not None:
        return existing, False
    # Race-safe insert: two concurrent /auth/session calls (Flutter fires it
    # from both the OTP-submit path and the authStateChanges listener) will
    # both miss the SELECT above. Catch the UNIQUE violation and re-fetch —
    # either by firebase_uid (concurrent-insert race) or by phone_e164 (the
    # same number re-registers under a new Firebase uid, e.g. account was
    # cleared or deleted-and-recreated in Firebase console).
    try:
        created = await users_repo.create(db, firebase_uid=firebase_uid, phone_e164=phone_e164)
        await db.commit()
        return created, True
    except IntegrityError:
        await db.rollback()
        winner = await users_repo.get_by_firebase_uid(db, firebase_uid)
        if winner is not None:
            return winner, False
        # phone_e164 collision — adopt the existing row into the new
        # Firebase identity so the user isn't locked out. Undelete if the
        # row had been soft-deleted so /me and Home stop rendering empties.
        by_phone = await _get_by_phone_any_status(db, phone_e164)
        if by_phone is None:
            raise
        by_phone.firebase_uid = firebase_uid
        if by_phone.status == RowStatus.deleted:
            by_phone.status = RowStatus.active
        by_phone.updated_by = by_phone.id
        await db.commit()
        await db.refresh(by_phone)
        return by_phone, False
