from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import RowStatus
from app.models.officer import Officer


async def get_by_firebase_uid(db: AsyncSession, uid: str) -> Officer | None:
    stmt = select(Officer).where(Officer.firebase_uid == uid, Officer.status != RowStatus.deleted)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_by_id(db: AsyncSession, officer_id: int) -> Officer | None:
    stmt = select(Officer).where(Officer.id == officer_id, Officer.status != RowStatus.deleted)
    return (await db.execute(stmt)).scalar_one_or_none()


async def create(
    db: AsyncSession,
    *,
    firebase_uid: str,
    employee_id: str,
    full_name: str,
    mobile_e164: str | None,
    email: str | None,
    pincode: str | None,
    block: str | None,
    state: str | None,
) -> Officer:
    officer = Officer(
        firebase_uid=firebase_uid,
        employee_id=employee_id,
        employee_id_verified=False,
        full_name=full_name,
        mobile_e164=mobile_e164,
        email=email,
        pincode=pincode,
        block=block,
        state=state,
    )
    db.add(officer)
    await db.flush()
    officer.created_by = officer.id
    officer.updated_by = officer.id
    await db.flush()
    return officer
