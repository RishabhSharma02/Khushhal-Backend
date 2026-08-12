
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import RowStatus
from app.models.user import User


async def get_by_firebase_uid(db: AsyncSession, uid: str) -> User | None:
    stmt = select(User).where(User.firebase_uid == uid, User.status != RowStatus.deleted)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
    stmt = select(User).where(User.id == user_id, User.status != RowStatus.deleted)
    return (await db.execute(stmt)).scalar_one_or_none()


async def create(db: AsyncSession, *, firebase_uid: str, phone_e164: str) -> User:
    user = User(firebase_uid=firebase_uid, phone_e164=phone_e164)
    db.add(user)
    await db.flush()
    # Self-audit: created_by = the user's own id (system self-signup convention).
    user.created_by = user.id
    user.updated_by = user.id
    await db.flush()
    return user
