
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.db.base import RowStatus
from app.models.business import Business
from app.models.monthly_snapshot import MonthlySnapshot
from app.models.user import User
from app.repositories import businesses as biz_repo
from app.schemas.business import BusinessCreate, BusinessUpdate
from app.services import insights_service
from app.services.officer import assignment_service

log = get_logger(__name__)


def _first_of_month(d: date | None = None) -> date:
    d = d or datetime.now(timezone.utc).date()
    return d.replace(day=1)


async def _stamp_first_score(db: AsyncSession, biz: Business, current: User) -> None:
    """Score a brand-new business immediately.

    The setup wizard's monthly snapshot is the only input the feature builder
    needs — zero ledger entries is a supported case — so there is nothing to
    wait for, and without this Home would sit on its loading skeleton until
    the monthly cron next runs. Scoring failures are swallowed: the score is
    recoverable (next stamp, or `POST /insights/refresh`), the business is
    not.
    """
    try:
        await insights_service.stamp_month(
            db, business=biz, user=current, as_on=datetime.now(timezone.utc).date(),
        )
    except Exception as e:
        log.warning("initial_stamp_failed", business_id=biz.id, err=str(e))
        await db.rollback()
        await db.refresh(biz)


async def _auto_assign_officer(biz: Business, current: User) -> None:
    """Assigns a field officer to a brand-new business. Same fire-and-forget
    safety as `_stamp_first_score` — a hiccup here (e.g. no officers
    provisioned yet) must never block onboarding. Runs in its own session
    (see assignment_service.auto_assign_officer), so unlike
    `_stamp_first_score` there's no request session state to recover here.
    """
    try:
        await assignment_service.auto_assign_officer(biz.id, current.state)
    except Exception as e:
        log.warning("auto_assign_failed", business_id=biz.id, err=str(e))


async def create_business(db: AsyncSession, current: User, payload: BusinessCreate) -> Business:
    biz = Business(
        user_id=current.id,
        name=payload.name,
        segment=payload.segment,
        sector=payload.sector,
        tenure=payload.tenure,
        staff_count=payload.staff_count,
        is_new_business=payload.is_new_business,
        years_in_operation=payload.years_in_operation,
        created_by=current.id,
        updated_by=current.id,
    )
    await biz_repo.create(db, biz)

    if payload.monthly is not None:
        snap = MonthlySnapshot(
            business_id=biz.id,
            month=_first_of_month(),
            money_in=payload.monthly.money_in,
            money_out=payload.monthly.money_out,
            loan_emi=payload.monthly.loan_emi,
            savings=payload.monthly.savings,
            basis=payload.monthly.basis,
            created_by=current.id,
            updated_by=current.id,
        )
        await biz_repo.create_snapshot(db, snap)

        # The savings figure typed on the setup wizard belongs to this
        # business, so it seeds the business row rather than the household
        # one. The wizard only collects a monthly EMI, not an outstanding
        # balance — surface that on Home's loan tile as an opening value
        # so it isn't zero after onboarding; the owner can replace it with
        # the true balance from the savings & loan screen.
        biz.savings_inr = payload.monthly.savings
        biz.loan_inr = payload.monthly.loan_emi

    await db.commit()
    await db.refresh(biz)
    # Runs before _stamp_first_score deliberately: the ML stamp's own
    # try/except can leave the request's async context in a state where
    # nothing else can safely await on it afterward (seen locally when the
    # lightgbm native lib fails to load) — assignment is cheap/deterministic
    # and shouldn't be at the mercy of that.
    await _auto_assign_officer(biz, current)
    await _stamp_first_score(db, biz, current)
    return biz


async def list_businesses(db: AsyncSession, current: User) -> list[Business]:
    return await biz_repo.list_for_user(db, current.id)


async def require_owned(db: AsyncSession, business_id: int, current: User) -> Business:
    biz = await biz_repo.get_owned(db, business_id, current.id)
    if biz is None:
        # 404 whether missing or unauthorized — do not leak existence.
        raise NotFoundError("Business not found")
    return biz


async def update_business(
    db: AsyncSession, business_id: int, current: User, payload: BusinessUpdate
) -> Business:
    biz = await require_owned(db, business_id, current)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(biz, field, value)
    biz.updated_by = current.id
    await db.commit()
    await db.refresh(biz)
    return biz


async def soft_delete_business(db: AsyncSession, business_id: int, current: User) -> None:
    biz = await require_owned(db, business_id, current)
    biz.status = RowStatus.deleted
    biz.updated_by = current.id
    await db.commit()
