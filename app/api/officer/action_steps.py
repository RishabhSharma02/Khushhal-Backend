from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.officer_security import get_current_officer
from app.db.session import get_db
from app.models.officer import Officer
from app.schemas.officer.action_steps import (
    ActionPlanSentRead,
    ActionStepCreate,
    ActionStepRead,
    ActionStepUpdate,
)
from app.services.officer import action_step_service

router = APIRouter(prefix="/enterprises/{business_id}/action-steps", tags=["officer-action-steps"])


@router.get("", response_model=list[ActionStepRead])
async def list_action_steps(
    business_id: int,
    db: AsyncSession = Depends(get_db),
    current: Officer = Depends(get_current_officer),
) -> list[ActionStepRead]:
    steps = await action_step_service.list_action_steps(db, current, business_id)
    return [ActionStepRead.model_validate(s) for s in steps]


@router.post("", response_model=ActionStepRead, status_code=status.HTTP_201_CREATED)
async def create_action_step(
    business_id: int,
    payload: ActionStepCreate,
    db: AsyncSession = Depends(get_db),
    current: Officer = Depends(get_current_officer),
) -> ActionStepRead:
    step = await action_step_service.create_action_step(db, current, business_id, payload)
    return ActionStepRead.model_validate(step)


@router.patch("/{step_id}", response_model=ActionStepRead)
async def update_action_step(
    business_id: int,
    step_id: int,
    payload: ActionStepUpdate,
    db: AsyncSession = Depends(get_db),
    current: Officer = Depends(get_current_officer),
) -> ActionStepRead:
    step = await action_step_service.update_action_step(db, current, business_id, step_id, payload)
    return ActionStepRead.model_validate(step)


@router.post("/send", response_model=ActionPlanSentRead)
async def send_action_plan(
    business_id: int,
    db: AsyncSession = Depends(get_db),
    current: Officer = Depends(get_current_officer),
) -> ActionPlanSentRead:
    alert_id, sent = await action_step_service.send_action_plan(db, current, business_id)
    return ActionPlanSentRead(alert_id=alert_id, steps_sent=len(sent))


@router.delete("/{step_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_action_step(
    business_id: int,
    step_id: int,
    db: AsyncSession = Depends(get_db),
    current: Officer = Depends(get_current_officer),
):
    await action_step_service.delete_action_step(db, current, business_id, step_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
