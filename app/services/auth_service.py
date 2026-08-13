
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories import users as users_repo


async def find_or_create_user_from_firebase(
    db: AsyncSession, firebase_uid: str, phone_e164: str
) -> User:
    user, _ = await find_or_create_returning_flag(db, firebase_uid, phone_e164)
    return user


async def find_or_create_returning_flag(
    db: AsyncSession, firebase_uid: str, phone_e164: str
) -> tuple[User, bool]:
    existing = await users_repo.get_by_firebase_uid(db, firebase_uid)
    if existing is not None:
        return existing, False
    # Race-safe insert: two concurrent /auth/session calls (Flutter fires it
    # from both the OTP-submit path and the authStateChanges listener) will
    # both miss the SELECT above. Catch the UNIQUE violation and re-fetch
    # so the loser returns the winning row instead of a 409.
    try:
        created = await users_repo.create(db, firebase_uid=firebase_uid, phone_e164=phone_e164)
        await db.commit()
        return created, True
    except IntegrityError:
        await db.rollback()
        winner = await users_repo.get_by_firebase_uid(db, firebase_uid)
        if winner is None:
            raise
        return winner, False
