from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.officer_security import get_current_officer
from app.db.session import get_db
from app.models.officer import Officer
from app.schemas.officer.contact_log import ContactLogEntryCreate, ContactLogEntryRead
from app.services.officer import contact_log_service

router = APIRouter(prefix="/enterprises/{business_id}/contact-log", tags=["officer-contact-log"])


@router.get("", response_model=list[ContactLogEntryRead])
async def list_contact_log(
    business_id: int,
    db: AsyncSession = Depends(get_db),
    current: Officer = Depends(get_current_officer),
) -> list[ContactLogEntryRead]:
    entries = await contact_log_service.list_contact_log(db, current, business_id)
    return [ContactLogEntryRead.model_validate(e) for e in entries]


@router.post("", response_model=ContactLogEntryRead, status_code=status.HTTP_201_CREATED)
async def create_contact_log_entry(
    business_id: int,
    payload: ContactLogEntryCreate,
    db: AsyncSession = Depends(get_db),
    current: Officer = Depends(get_current_officer),
) -> ContactLogEntryRead:
    entry = await contact_log_service.create_contact_log_entry(db, current, business_id, payload)
    return ContactLogEntryRead.model_validate(entry)
