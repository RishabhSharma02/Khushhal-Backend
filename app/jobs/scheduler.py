"""APScheduler wiring — one AsyncIOScheduler per process.

Started in FastAPI's lifespan. Only the monthly stamp job is scheduled for
now; anything more elaborate belongs in a dedicated worker process.
"""
from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.logging import get_logger
from app.jobs.stamp_monthly import run as stamp_monthly

log = get_logger("jobs.scheduler")

_scheduler: AsyncIOScheduler | None = None


def start() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    sched = AsyncIOScheduler(timezone="UTC")
    sched.add_job(
        stamp_monthly,
        trigger=CronTrigger(day=1, hour=0, minute=5, timezone="UTC"),
        id="stamp_monthly",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    sched.start()
    _scheduler = sched
    log.info("scheduler_started", jobs=[j.id for j in sched.get_jobs()])
    return sched


def stop() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("scheduler_stopped")
