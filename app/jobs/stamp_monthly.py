"""Monthly stamp job.

Iterates every business with recent activity and calls
`insights_service.stamp_month(business, as_on=first_of_month)`. Idempotent —
safe to re-run for the same `as_on`.

Callable both from APScheduler and from the CLI:
    python -m app.jobs.stamp_monthly              # today's first-of-month
    python -m app.jobs.stamp_monthly 2026-08-01   # explicit as-on
"""
from __future__ import annotations

import asyncio
import sys
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.core.logging import configure_logging, get_logger
from app.db.base import RowStatus
from app.db.session import SessionLocal
from app.models.business import Business
from app.models.user import User
from app.repositories import insights as insights_repo
from app.services import insights_service


def _first_of_month(d: date) -> date:
    return d.replace(day=1)


async def run(as_on: date | None = None) -> dict:
    log = get_logger("jobs.stamp_monthly")
    as_on = _first_of_month(as_on or datetime.now(timezone.utc).date())
    since = _first_of_month(as_on - timedelta(days=190))

    scored = 0
    failed = 0
    async with SessionLocal() as db:
        biz_ids = await insights_repo.business_ids_with_recent_activity(db, since)
        if not biz_ids:
            log.info("stamp_month_no_eligible_businesses", as_on=as_on.isoformat())
            return {"as_on": as_on.isoformat(), "scored": 0, "failed": 0}

        for bid in biz_ids:
            biz = (await db.execute(
                select(Business).where(Business.id == bid, Business.status != RowStatus.deleted)
            )).scalar_one_or_none()
            if biz is None:
                continue
            user = (await db.execute(
                select(User).where(User.id == biz.user_id, User.status != RowStatus.deleted)
            )).scalar_one_or_none()
            if user is None:
                continue
            try:
                await insights_service.stamp_month(db, business=biz, user=user, as_on=as_on)
                scored += 1
            except Exception as e:
                failed += 1
                log.exception("stamp_month_business_failed", business_id=bid, err=str(e))

    log.info("stamp_month_complete", as_on=as_on.isoformat(), scored=scored, failed=failed)
    return {"as_on": as_on.isoformat(), "scored": scored, "failed": failed}


def _parse_as_on(arg: str | None) -> date | None:
    if not arg:
        return None
    return datetime.strptime(arg, "%Y-%m-%d").date()


if __name__ == "__main__":  # pragma: no cover
    configure_logging()
    as_on = _parse_as_on(sys.argv[1] if len(sys.argv) > 1 else None)
    asyncio.run(run(as_on))
