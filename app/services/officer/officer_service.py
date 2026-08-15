from sqlalchemy.ext.asyncio import AsyncSession

from app.core.officer_security import OfficerFirebaseIdentity
from app.models.officer import Officer
from app.repositories.officer import officers as officers_repo
from app.schemas.officer.profile import OfficerRegister, OfficerUpdate


async def update_officer(db: AsyncSession, officer: Officer, payload: OfficerUpdate) -> Officer:
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(officer, field, value)
    officer.updated_by = officer.id
    await db.commit()
    await db.refresh(officer)
    return officer


async def register_officer(
    db: AsyncSession, identity: OfficerFirebaseIdentity, payload: OfficerRegister
) -> Officer:
    """Creates the `officers` row for a Firebase account the app just
    created via createUserWithEmailAndPassword. Idempotent on firebase_uid
    (a retried/double-submitted registration returns the existing row
    rather than erroring) — duplicate employee_id/mobile_e164 across
    *different* officers still 409s via the unique constraints, handled by
    the global IntegrityError handler.
    """
    existing = await officers_repo.get_by_firebase_uid(db, identity.uid)
    if existing is not None:
        return existing

    officer = await officers_repo.create(
        db,
        firebase_uid=identity.uid,
        employee_id=payload.employee_id,
        full_name=payload.full_name,
        mobile_e164=payload.mobile_e164,
        email=identity.email,
        pincode=payload.pincode,
        block=payload.block,
        state=payload.state,
    )
    await db.commit()
    await db.refresh(officer)
    return officer
