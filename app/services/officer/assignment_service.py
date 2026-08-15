from __future__ import annotations

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.officer_assignment import OfficerEnterpriseAssignment
from app.repositories.officer import assignments as assignments_repo

log = get_logger(__name__)


async def auto_assign_officer(
    business_id: int, owner_state: str | None
) -> OfficerEnterpriseAssignment | None:
    """Assigns a newly onboarded business to a field officer: the
    least-loaded active officer whose posting state matches `owner_state`,
    falling back to the least-loaded active officer overall if there's no
    state match (or `owner_state` is blank).

    Runs in its own session rather than reusing the caller's — onboarding's
    own request session may already be mid-transaction or have just
    recovered from an unrelated failure (e.g. `_stamp_first_score`), and
    auto-assignment must not inherit that state. Commits on success.

    Returns `None`, leaving the business unassigned, if there are no active
    officers at all yet — this never raises, so an empty officer roster
    can't block business creation.
    """
    async with SessionLocal() as db:
        officer = await assignments_repo.least_loaded_officer(db, state=owner_state)
        matched_by_state = officer is not None
        if officer is None:
            officer = await assignments_repo.least_loaded_officer(db, state=None)
        if officer is None:
            log.warning("auto_assign_no_officers_available", business_id=business_id)
            return None

        assignment = await assignments_repo.create(
            db, officer_id=officer.id, business_id=business_id
        )
        await db.commit()
        log.info(
            "auto_assign_officer",
            business_id=business_id,
            officer_id=officer.id,
            matched_by_state=matched_by_state,
        )
        return assignment
