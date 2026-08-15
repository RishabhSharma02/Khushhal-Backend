from fastapi import APIRouter

from app.api.v1 import auth, businesses, insights, ledger, locations, officers, profile, users

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(profile.router)
router.include_router(businesses.router)
router.include_router(ledger.router)
router.include_router(insights.router)
router.include_router(locations.router)
router.include_router(officers.router)

__all__ = ["router"]
