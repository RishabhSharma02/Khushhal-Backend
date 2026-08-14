from fastapi import APIRouter

from app.api.officer import (
    action_steps,
    auth,
    contact_log,
    dashboard,
    enterprises,
    profile,
    reports,
    sync_status,
    visits,
)

router = APIRouter(prefix="/api/officer/v1")
router.include_router(auth.router)
router.include_router(profile.router)
router.include_router(enterprises.router)
router.include_router(action_steps.router)
router.include_router(contact_log.router)
router.include_router(visits.router)
router.include_router(sync_status.router)
router.include_router(dashboard.router)
router.include_router(reports.router)

__all__ = ["router"]
