
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories import users as users_repo


async def find_or_create_user_from_firebase(
    db: AsyncSession, firebase_uid: str, phone_e164: str
) -> User:
    user = await users_repo.get_by_firebase_uid(db, firebase_uid)
    if user is not None:
        return user
    user = await users_repo.create(db, firebase_uid=firebase_uid, phone_e164=phone_e164)
    await db.commit()
    return user


async def find_or_create_returning_flag(
    db: AsyncSession, firebase_uid: str, phone_e164: str
) -> tuple[User, bool]:
    existing = await users_repo.get_by_firebase_uid(db, firebase_uid)
    if existing is not None:
        return existing, False
    created = await users_repo.create(db, firebase_uid=firebase_uid, phone_e164=phone_e164)
    await db.commit()
    return created, True
