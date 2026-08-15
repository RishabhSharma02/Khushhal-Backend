from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import RowStatus
from app.models.risk_alert import RiskAlert


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
