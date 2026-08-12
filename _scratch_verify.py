"""Throwaway verification for the stamp_month alert-resolution change and the
create-business initial stamp. Deleted after use."""
import asyncio
from datetime import date

from sqlalchemy import select, text

from app.db.session import SessionLocal
from app.models.business import Business, BusinessSector, BusinessSegment, BusinessTenure
from app.models.monthly_snapshot import MoneyBasis
from app.models.user import User
from app.schemas.business import BusinessCreate, MonthlyMoneyIn
from app.services import business_service, insights_service


async def dump(db, label):
    print(f"\n--- {label}")
    rows = (await db.execute(text(
        "select id, business_id, as_on, kind, resolved_at from risk_alerts order by business_id, as_on"
    ))).all()
    for r in rows:
        print("  alert", r)


async def main():
    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.id == 14))).scalar_one()
        biz = (await db.execute(select(Business).where(Business.id == 1))).scalar_one()

        await dump(db, "before")
        print(biz.id, insights_service, date)

        print("\ncreating a fresh business (no ledger entries) ...")
        created = await business_service.create_business(
            db,
            user,
            BusinessCreate(
                name="ZZ Scratch Verify",
                segment=BusinessSegment.own,
                sector=BusinessSector.dairy,
                tenure=BusinessTenure.under_1,
                staff_count=1,
                is_new_business=True,
                years_in_operation=0,
                monthly=MonthlyMoneyIn(
                    money_in=30000, money_out=20000, loan_emi=0,
                    savings=5000, basis=MoneyBasis.rough,
                ),
            ),
        )
        print("  new business id", created.id)
        hs = (await db.execute(text(
            "select as_on, score, band, risk from health_scores where business_id = :b"
        ), {"b": created.id})).all()
        fc = (await db.execute(text(
            "select count(*), sum(case when is_risk_month then 1 else 0 end) "
            "from forecasts where business_id = :b"
        ), {"b": created.id})).all()
        al = (await db.execute(text(
            "select as_on, kind, severity from risk_alerts where business_id = :b"
        ), {"b": created.id})).all()
        print("  health:", hs)
        print("  forecast rows / flagged:", fc)
        print("  alerts:", al)

        print("\ncleaning up ...")
        await db.execute(text("delete from plan_actions where alert_id in (select id from risk_alerts where business_id = :b)"), {"b": created.id})
        await db.execute(text("delete from risk_alerts where business_id = :b"), {"b": created.id})
        await db.execute(text("delete from forecasts where business_id = :b"), {"b": created.id})
        await db.execute(text("delete from health_scores where business_id = :b"), {"b": created.id})
        await db.execute(text("delete from monthly_snapshots where business_id = :b"), {"b": created.id})
        await db.execute(text("delete from businesses where id = :b"), {"b": created.id})
        # Roll business 1 back to the single-August state described in the task.
        await db.execute(text("delete from plan_actions where alert_id in (select id from risk_alerts where business_id = 1 and as_on = '2026-09-01')"))
        await db.execute(text("delete from risk_alerts where business_id = 1 and as_on = '2026-09-01'"))
        await db.execute(text("delete from forecasts where business_id = 1 and as_on = '2026-09-01'"))
        await db.execute(text("delete from health_scores where business_id = 1 and as_on = '2026-09-01'"))
        await db.execute(text("update risk_alerts set resolved_at = null where business_id = 1"))
        await db.commit()
        await dump(db, "after cleanup")


asyncio.run(main())
