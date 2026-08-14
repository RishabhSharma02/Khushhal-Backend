import uuid
from datetime import date, datetime, timedelta, timezone

import asyncpg
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from main import app


@pytest.fixture(scope="session")
def client():
    """One TestClient portal (one event loop) for the whole officer test
    session. A bare `TestClient(app)` opens a *new* event loop per call, but
    the app's async SQLAlchemy engine is a single global connection pool —
    reusing a pooled connection from a since-closed loop crashes on the
    `pool_pre_ping` check. `with TestClient(app) as c:` keeps one loop alive
    for every request made through `c`, matching the pool's lifetime.
    """
    with TestClient(app) as c:
        yield c


def _raw_dsn() -> str:
    # asyncpg.connect() wants a plain postgresql:// DSN, not SQLAlchemy's
    # postgresql+asyncpg:// form.
    return get_settings().database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


@pytest.fixture
def seeded_officer():
    """Creates a test officer, cleans it up after the test.

    Uses a standalone asyncpg connection (its own throwaway event loop via
    asyncio.run) rather than the app's SessionLocal/engine — reusing the
    app's pooled engine here would leave a connection bound to this loop
    sitting in the pool, which the `client` fixture's *different* loop would
    then crash on. A one-off connection outside the pool has no such
    lifetime coupling.
    """
    import asyncio

    async def _create() -> int:
        conn = await asyncpg.connect(_raw_dsn())
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO officers
                    (firebase_uid, employee_id, employee_id_verified, mobile_e164,
                     full_name, block, state)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                "test-officer-uid",
                "TEST-EMP-001",
                True,
                "+919999999999",
                "Test Officer",
                "Test Block",
                "Test State",
            )
            officer_id = row["id"]
            await conn.execute(
                "UPDATE officers SET created_by = $1, updated_by = $1 WHERE id = $1", officer_id
            )
            return officer_id
        finally:
            await conn.close()

    async def _delete(officer_id: int) -> None:
        conn = await asyncpg.connect(_raw_dsn())
        try:
            await conn.execute("DELETE FROM officers WHERE id = $1", officer_id)
        finally:
            await conn.close()

    officer_id = asyncio.run(_create())
    yield officer_id
    asyncio.run(_delete(officer_id))


@pytest.fixture
def seeded_enterprise(seeded_officer):
    """A minimal assigned business — user, business, snapshot, health score,
    risk alert, ledger entries, contact, assignment — for the enterprises
    endpoints. Depends on seeded_officer so it's assigned to that officer
    and cleaned up in the same test.
    """
    import asyncio

    async def _create() -> int:
        conn = await asyncpg.connect(_raw_dsn())
        try:
            user_id = (
                await conn.fetchval(
                    """
                    INSERT INTO users (firebase_uid, phone_e164, name, village, savings_inr, loan_inr)
                    VALUES ($1, $2, $3, $4, $5, $6) RETURNING id
                    """,
                    "test-owner-uid",
                    "+911111111111",
                    "Test Owner",
                    "Test Village",
                    5000,
                    2000,
                )
            )
            await conn.execute("UPDATE users SET created_by=$1, updated_by=$1 WHERE id=$1", user_id)

            business_id = (
                await conn.fetchval(
                    """
                    INSERT INTO businesses
                        (user_id, name, segment, sector, tenure, staff_count,
                         is_new_business, years_in_operation, created_by, updated_by)
                    VALUES ($1, 'Test Dairy', 'shg', 'dairy', '3_to_10', 2,
                            false, 5, $1, $1)
                    RETURNING id
                    """,
                    user_id,
                )
            )

            month_start = date.today().replace(day=1)
            await conn.execute(
                """
                INSERT INTO monthly_snapshots
                    (business_id, month, money_in, money_out, loan_emi, savings, basis, created_by, updated_by)
                VALUES ($1, $2, 10000, 8000, 500, 5000, 'records', $3, $3)
                """,
                business_id, month_start, user_id,
            )
            await conn.execute(
                """
                INSERT INTO health_scores
                    (business_id, as_on, next_update, score, risk, delta, band,
                     p_green, p_amber, p_red, model_version, created_by, updated_by)
                VALUES ($1, $2, $2, 60, 'medium', 2, 'amber', 0.3, 0.5, 0.2, 'test', $3, $3)
                """,
                business_id, month_start, user_id,
            )
            await conn.execute(
                """
                INSERT INTO risk_alerts
                    (business_id, as_on, kind, severity, driver, has_plan, raised_on, created_by, updated_by)
                VALUES ($1, $2, 'savings_low', 'info', 'Test flag driver', true, $2, $3, $3)
                """,
                business_id, month_start, user_id,
            )
            now = datetime.now(timezone.utc)
            for i in range(3):
                await conn.execute(
                    """
                    INSERT INTO ledger_entries
                        (business_id, user_id, kind, amount_inr, category, recorded_at,
                         source, client_entry_id, created_by, updated_by)
                    VALUES ($1, $2, 'in', 1000, 'milk_sale', $3, 'manual', $4, $2, $2)
                    """,
                    business_id, user_id, now - timedelta(days=i), uuid.uuid4(),
                )
            await conn.execute(
                """
                INSERT INTO enterprise_contacts (business_id, name, role, phone, language, best_time, created_by, updated_by)
                VALUES ($1, 'Test Owner', 'owner', '+911111111111', 'Hindi', 'mornings', $2, $2)
                """,
                business_id, seeded_officer,
            )
            await conn.execute(
                """
                INSERT INTO officer_enterprise_assignments (officer_id, business_id, created_by, updated_by)
                VALUES ($1, $2, $1, $1)
                """,
                seeded_officer, business_id,
            )
            return business_id
        finally:
            await conn.close()

    async def _delete(business_id: int) -> None:
        conn = await asyncpg.connect(_raw_dsn())
        try:
            user_id = await conn.fetchval("SELECT user_id FROM businesses WHERE id=$1", business_id)
            await conn.execute("DELETE FROM officer_enterprise_assignments WHERE business_id=$1", business_id)
            await conn.execute("DELETE FROM enterprise_contacts WHERE business_id=$1", business_id)
            await conn.execute("DELETE FROM risk_alerts WHERE business_id=$1", business_id)
            await conn.execute("DELETE FROM health_scores WHERE business_id=$1", business_id)
            await conn.execute("DELETE FROM monthly_snapshots WHERE business_id=$1", business_id)
            await conn.execute("DELETE FROM ledger_entries WHERE business_id=$1", business_id)
            await conn.execute("DELETE FROM businesses WHERE id=$1", business_id)
            if user_id is not None:
                await conn.execute("DELETE FROM users WHERE id=$1", user_id)
        finally:
            await conn.close()

    business_id = asyncio.run(_create())
    yield business_id
    asyncio.run(_delete(business_id))
