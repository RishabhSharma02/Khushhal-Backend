
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories import insights as insights_repo
from app.schemas.insights import (
    ForecastMonthRead,
    ForecastRead,
    HealthRead,
    PlanActionRead,
    PlanActionUpdate,
    RiskAlertDetail,
    RiskAlertRead,
)
from app.services import business_service
from app.services import insights_service

router = APIRouter(tags=["insights"], prefix="/businesses/{business_id}")


@router.get("/health", response_model=HealthRead)
async def get_health(
    business_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> HealthRead:
    await business_service.require_owned(db, business_id, current)
    row = await insights_repo.latest_health(db, business_id)
    if row is None:
        raise NotFoundError("No score stamped yet — try POST /insights/refresh (dev)")
    return HealthRead.model_validate(row)


@router.get("/forecast", response_model=ForecastRead)
async def get_forecast(
    business_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> ForecastRead:
    await business_service.require_owned(db, business_id, current)
    rows = await insights_repo.latest_forecast(db, business_id)
    if not rows:
        raise NotFoundError("No forecast stamped yet")
    return ForecastRead(
        business_id=business_id,
        as_on=rows[0].as_on,
        months=[ForecastMonthRead.model_validate(r) for r in rows],
    )


@router.get("/alerts", response_model=list[RiskAlertRead])
async def list_alerts(
    business_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[RiskAlertRead]:
    await business_service.require_owned(db, business_id, current)
    rows = await insights_repo.active_alerts(db, business_id)
    return [RiskAlertRead.model_validate(r) for r in rows]


@router.get("/alerts/{alert_id}", response_model=RiskAlertDetail)
async def get_alert(
    business_id: int,
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> RiskAlertDetail:
    await business_service.require_owned(db, business_id, current)
    row = await insights_repo.alert_with_plan(db, business_id, alert_id)
    if row is None:
        raise NotFoundError("Alert not found")
    return RiskAlertDetail(
        **RiskAlertRead.model_validate(row).model_dump(),
        plan_actions=[PlanActionRead.model_validate(a) for a in sorted(row.plan_actions, key=lambda a: (a.role.value, a.ordinal))],
    )


@router.patch("/alerts/{alert_id}/actions/{action_id}", response_model=PlanActionRead)
async def patch_plan_action(
    business_id: int,
    alert_id: int,
    action_id: int,
    payload: PlanActionUpdate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> PlanActionRead:
    await business_service.require_owned(db, business_id, current)
    updated = await insights_service.toggle_plan_action(
        db, action_id=action_id, done=payload.done, current=current,
    )
    return PlanActionRead.model_validate(updated)


@router.post("/insights/refresh", response_model=HealthRead)
@limiter.limit("10/minute")
async def refresh_insights(
    request: Request,
    business_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> HealthRead:
    """Dev-gated force-recompute.

    Runs the monthly stamp job for this business right now, so the health /
    forecast / alerts endpoints return fresh output without waiting for the
    APScheduler cron. Only exposed when `DEV_TOOLS_ENABLED=true`.
    """
    if not settings.dev_tools_enabled:
        raise ForbiddenError("Dev tools disabled")
    biz = await business_service.require_owned(db, business_id, current)
    today = datetime.now(timezone.utc).date()
    stamped = await insights_service.stamp_month(
        db, business=biz, user=current, as_on=today,
    )
    return HealthRead.model_validate(stamped)
