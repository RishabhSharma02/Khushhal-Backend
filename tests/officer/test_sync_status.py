import asyncio

import asyncpg

from tests.officer.conftest import _raw_dsn

HEADERS = {"X-Debug-Firebase-Uid": "test-officer-uid"}


async def _run(*statements: str) -> None:
    conn = await asyncpg.connect(_raw_dsn())
    try:
        for stmt in statements:
            await conn.execute(stmt)
    finally:
        await conn.close()


def test_fresh_business_has_no_stale_rows(client, seeded_enterprise):
    response = client.get("/api/officer/v1/sync-status", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == []
    assert body["synced_under_24h_count"] + body["synced_1_to_7_days_count"] + body[
        "synced_stale_7_plus_count"
    ] == 1


def test_never_synced_old_business_is_stale(client, seeded_enterprise):
    asyncio.run(
        _run(
            f"UPDATE businesses SET creation_date = now() - interval '60 days' "
            f"WHERE id = {seeded_enterprise}",
            f"UPDATE ledger_entries SET recorded_at = now() - interval '9 days' "
            f"WHERE business_id = {seeded_enterprise}",
        )
    )

    response = client.get("/api/officer/v1/sync-status", headers=HEADERS)
    body = response.json()
    assert body["synced_stale_7_plus_count"] == 1
    assert body["entry_gap_5_plus_count"] == 1
    row = next(r for r in body["rows"] if r["enterprise_id"] == str(seeded_enterprise))
    assert row["action_kind"] == "resendLogin"


def test_syncing_but_not_entering(client, seeded_enterprise):
    business_id = seeded_enterprise
    asyncio.run(
        _run(
            f"UPDATE ledger_entries SET recorded_at = now() - interval '9 days' "
            f"WHERE business_id = {business_id}",
        )
    )

    async def _seed_sync_event() -> None:
        conn = await asyncpg.connect(_raw_dsn())
        try:
            user_id = await conn.fetchval(
                "SELECT user_id FROM businesses WHERE id = $1", business_id
            )
            await conn.execute(
                """
                INSERT INTO sync_events (user_id, batch_size, accepted, duplicates, created_by, updated_by)
                VALUES ($1, 3, 3, 0, $1, $1)
                """,
                user_id,
            )
        finally:
            await conn.close()

    asyncio.run(_seed_sync_event())

    response = client.get("/api/officer/v1/sync-status", headers=HEADERS)
    body = response.json()
    row = next(r for r in body["rows"] if r["enterprise_id"] == str(business_id))
    assert row["action_kind"] == "addToRoute"
    assert "not entering" in row["likely_cause"]


def test_sync_status_unauthorized_without_token(client):
    response = client.get("/api/officer/v1/sync-status")
    assert response.status_code == 401
