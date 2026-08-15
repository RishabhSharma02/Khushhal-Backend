from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, NotFoundError
from app.db.base import RowStatus
from app.models.action_step import OfficerActionStep
from app.models.officer import Officer
from app.models.risk_alert import PlanAction
from app.repositories.officer import action_steps as action_steps_repo
from app.repositories.officer import alerts as alerts_repo
from app.repositories.officer import assignments as assignments_repo
from app.schemas.officer.action_steps import ActionStepCreate, ActionStepUpdate


async def _require_assigned(db: AsyncSession, officer_id: int, business_id: int) -> None:
    if not await assignments_repo.is_assigned(db, officer_id, business_id):
        raise NotFoundError("Enterprise not found")


async def list_action_steps(
    db: AsyncSession, officer: Officer, business_id: int
) -> list[OfficerActionStep]:
    await _require_assigned(db, officer.id, business_id)
    return await action_steps_repo.list_for_business(db, business_id)


async def create_action_step(
    db: AsyncSession, officer: Officer, business_id: int, payload: ActionStepCreate
) -> OfficerActionStep:
    await _require_assigned(db, officer.id, business_id)
    ordinal = await action_steps_repo.next_ordinal(db, business_id)
    step = OfficerActionStep(
        business_id=business_id,
        ordinal=ordinal,
        title=payload.title,
        detail=payload.detail,
        impact=payload.impact,
        created_by=officer.id,
        updated_by=officer.id,
    )
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return step


async def update_action_step(
    db: AsyncSession, officer: Officer, business_id: int, step_id: int, payload: ActionStepUpdate
) -> OfficerActionStep:
    await _require_assigned(db, officer.id, business_id)
    step = await action_steps_repo.get_owned(db, step_id, business_id)
    if step is None:
        raise NotFoundError("Action step not found")

    step.title = payload.title
    step.detail = payload.detail
    step.impact = payload.impact
    step.updated_by = officer.id
    await db.commit()
    await db.refresh(step)
    return step


async def delete_action_step(db: AsyncSession, officer: Officer, business_id: int, step_id: int) -> None:
    await _require_assigned(db, officer.id, business_id)
    step = await action_steps_repo.get_owned(db, step_id, business_id)
    if step is None:
        raise NotFoundError("Action step not found")

    step.status = RowStatus.deleted
    step.updated_by = officer.id
    await db.flush()

    # Renumber the survivors 1..N, matching the frontend's in-memory
    # behaviour before this had a backend.
    remaining = await action_steps_repo.list_for_business(db, business_id)
    for index, remaining_step in enumerate(remaining, start=1):
        remaining_step.ordinal = index
        remaining_step.updated_by = officer.id

    await db.commit()


async def send_action_plan(
    db: AsyncSession, officer: Officer, business_id: int
) -> tuple[int, list[PlanAction]]:
    """Publishes the officer's current action-plan steps to the business's
    latest open alert as `field_officer`-role plan actions — the same shape
    the owner's app already renders for ML-authored plans (see
    `alert_detail_screen.dart`'s owner-then-field_officer fallback), so no
    consumer-side change is needed. Each send replaces the previous one.
    """
    await _require_assigned(db, officer.id, business_id)
    alert = await alerts_repo.latest_open_alert(db, business_id)
    if alert is None:
        raise AppError(
            "no_open_alert",
            "This enterprise has no open flag to attach the plan to yet.",
            status_code=409,
        )

    steps = await action_steps_repo.list_for_business(db, business_id)
    sent = await alerts_repo.replace_field_officer_plan(db, alert.id, steps)
    await db.commit()
    for action in sent:
        await db.refresh(action)
    return alert.id, sent
