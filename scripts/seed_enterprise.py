"""Dev-only: seed a "Shanti Dairy" business (owner, ledger entries, snapshot,
health score, forecast, risk alert, contact) and assign it to a test
officer, so Phase 1's enterprises endpoints — and the officer portal UI —
have something real to show before an admin-provisioning tool exists.

Usage:
    .venv/bin/python -m scripts.seed_enterprise --officer-firebase-uid dev-officer-1

Refuses to run unless DEV_TOOLS_ENABLED=true. Idempotent: re-running skips
whatever's already there (matched by firebase_uid / business name).
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import get_settings
from app.db.base import RowStatus
from app.db.session import SessionLocal
from app.models.business import Business, BusinessSector, BusinessSegment, BusinessTenure
from app.models.enterprise_contact import EnterpriseContact
from app.models.forecast import Forecast
from app.models.health_score import HealthScore, RiskLevel, ScoreBand
from app.models.ledger_entry import EntryCategory, EntryKind, EntrySource, LedgerEntry
from app.models.monthly_snapshot import MoneyBasis, MonthlySnapshot
from app.models.officer_assignment import OfficerEnterpriseAssignment
from app.models.risk_alert import AlertKind, AlertSeverity, RiskAlert
from app.models.user import User
from app.repositories.officer import officers as officers_repo


async def _seed(args: argparse.Namespace) -> None:
    settings = get_settings()
    if not settings.dev_tools_enabled:
        print("Refusing to seed: DEV_TOOLS_ENABLED is not true.", file=sys.stderr)
        raise SystemExit(1)

    async with SessionLocal() as db:
        officer = await officers_repo.get_by_firebase_uid(db, args.officer_firebase_uid)
        if officer is None:
            print(
                f"No officer with firebase_uid={args.officer_firebase_uid!r} — "
                "run scripts.seed_officer first.",
                file=sys.stderr,
            )
            raise SystemExit(1)

        existing = (
            await db.execute(
                select(Business).where(Business.name == "Shanti Dairy", Business.status != RowStatus.deleted)
            )
        ).scalar_one_or_none()
        if existing is not None:
            print(f"Shanti Dairy already exists: business_id={existing.id}")
            return

        owner = User(
            firebase_uid="dev-owner-shanti-dairy",
            phone_e164="+919876543210",
            name="Sunita Devi",
            state="UP",
            district="Sitapur",
            village="Rampur",
            savings_inr=31000,
            loan_inr=86000,
        )
        db.add(owner)
        await db.flush()
        owner.created_by = owner.id
        owner.updated_by = owner.id

        business = Business(
            user_id=owner.id,
            name="Shanti Dairy",
            segment=BusinessSegment.shg,
            sector=BusinessSector.dairy,
            tenure=BusinessTenure.three_to_ten,
            staff_count=4,
            is_new_business=False,
            years_in_operation=date.today().year - 2018,
            created_by=owner.id,
            updated_by=owner.id,
        )
        db.add(business)
        await db.flush()

        db.add(
            EnterpriseContact(
                business_id=business.id,
                name="Sunita Devi",
                role="owner",
                phone="+919876543210",
                language="Hindi",
                best_time="6-8 pm",
                created_by=officer.id,
                updated_by=officer.id,
            )
        )

        now = datetime.now(timezone.utc)
        ledger_rows = [
            (EntryKind.in_, 4200, EntryCategory.milk_sale, now - timedelta(days=0, hours=2)),
            (EntryKind.out, 900, EntryCategory.fodder, now - timedelta(days=1)),
            (EntryKind.in_, 3900, EntryCategory.milk_sale, now - timedelta(days=1, hours=5)),
            (EntryKind.out, 1200, EntryCategory.vet, now - timedelta(days=2)),
            (EntryKind.in_, 4100, EntryCategory.milk_sale, now - timedelta(days=3)),
            (EntryKind.out, 8000, EntryCategory.emi, now - timedelta(days=4)),
        ]
        for kind, amount, category, recorded_at in ledger_rows:
            db.add(
                LedgerEntry(
                    business_id=business.id,
                    user_id=owner.id,
                    kind=kind,
                    amount_inr=amount,
                    category=category,
                    recorded_at=recorded_at,
                    source=EntrySource.manual,
                    client_entry_id=uuid.uuid4(),
                    created_by=owner.id,
                    updated_by=owner.id,
                )
            )

        month_start = date.today().replace(day=1)
        db.add(
            MonthlySnapshot(
                business_id=business.id,
                month=month_start,
                money_in=41000,
                money_out=35800,
                loan_emi=8000,
                savings=31000,
                basis=MoneyBasis.records,
                created_by=owner.id,
                updated_by=owner.id,
            )
        )

        db.add(
            HealthScore(
                business_id=business.id,
                as_on=month_start,
                next_update=(month_start.replace(day=28) + timedelta(days=4)).replace(day=1),
                score=38,
                risk=RiskLevel.high,
                delta=-3,
                days_written=22,
                days_in_month=30,
                band=ScoreBand.red,
                p_green=0.10,
                p_amber=0.25,
                p_red=0.65,
                model_version="seed",
                created_by=owner.id,
                updated_by=owner.id,
            )
        )

        db.add(
            RiskAlert(
                business_id=business.id,
                as_on=month_start,
                kind=AlertKind.liquidity_debt_stress,
                severity=AlertSeverity.urgent,
                driver="Nov gap ₹32k forecast",
                has_plan=True,
                raised_on=date.today(),
                created_by=owner.id,
                updated_by=owner.id,
            )
        )

        for horizon in range(1, 7):
            db.add(
                Forecast(
                    business_id=business.id,
                    as_on=month_start,
                    horizon=horizon,
                    cf_pred=5200.0 - (9200.0 if horizon == 3 else 0.0),
                    in_level=0.55,
                    out_level=0.60 if horizon != 3 else 0.85,
                    is_risk_month=(horizon == 3),
                    created_by=owner.id,
                    updated_by=owner.id,
                )
            )

        db.add(
            OfficerEnterpriseAssignment(
                officer_id=officer.id,
                business_id=business.id,
                created_by=officer.id,
                updated_by=officer.id,
            )
        )

        await db.commit()
        print(f"Seeded Shanti Dairy: business_id={business.id}, owner_id={owner.id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--officer-firebase-uid", default="dev-officer-1")
    args = parser.parse_args()
    asyncio.run(_seed(args))


if __name__ == "__main__":
    main()
