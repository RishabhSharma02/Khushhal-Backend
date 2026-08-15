from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import RowStatus
from app.models.action_step import OfficerActionStep
from app.models.risk_alert import PlanAction, PlanActionRole, RiskAlert


async def list_for_business(db: AsyncSession, business_id: int) -> list[RiskAlert]:
    """All alerts for a business, resolved or not — unlike
    app.repositories.insights.active_alerts, which only returns open ones.
    """
    stmt = (
        select(RiskAlert)
        .where(RiskAlert.business_id == business_id, RiskAlert.status != RowStatus.deleted)
        .order_by(RiskAlert.raised_on.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def latest_open_alert(db: AsyncSession, business_id: int) -> RiskAlert | None:
    """The business's most recently raised unresolved alert — where a
    "Send plan" from the officer portal attaches, since `plan_actions`
    always belongs to one alert. `None` if the business has no open alert.
    """
    stmt = (
        select(RiskAlert)
        .where(
            RiskAlert.business_id == business_id,
            RiskAlert.status != RowStatus.deleted,
            RiskAlert.resolved_at.is_(None),
        )
        .order_by(RiskAlert.raised_on.desc(), RiskAlert.id.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def replace_field_officer_plan(
    db: AsyncSession, alert_id: int, steps: list[OfficerActionStep]
) -> list[PlanAction]:
    """Replaces the alert's `field_officer`-role plan actions with the
    officer's current action-plan steps — each "Send plan" supersedes the
    last, so the owner's app never shows a stale or duplicated plan.
    `owner`-role (ML-authored) actions on the same alert are untouched.
    """
    existing_stmt = select(PlanAction).where(
        PlanAction.alert_id == alert_id,
        PlanAction.role == PlanActionRole.field_officer,
        PlanAction.status != RowStatus.deleted,
    )
    for existing in (await db.execute(existing_stmt)).scalars().all():
        existing.status = RowStatus.deleted

    created: list[PlanAction] = []
    for step in steps:
        label = f"{step.title}: {step.detail}" if step.detail else step.title
        action = PlanAction(
            alert_id=alert_id,
            role=PlanActionRole.field_officer,
            ordinal=step.ordinal,
            label_en=label,
        )
        db.add(action)
        created.append(action)
    await db.flush()
    return created
