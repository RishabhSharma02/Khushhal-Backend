import asyncio

import asyncpg
import pytest

from tests.officer.conftest import _raw_dsn

BUSINESS_PAYLOAD = {
    "name": "Auto Assign Dairy",
    "segment": "shg",
    "sector": "dairy",
    "tenure": "3_to_10",
    "staff_count": 1,
}


def _run(coro):
    return asyncio.run(coro)


async def _create_officer(*, employee_id: str, state: str | None) -> int:
    conn = await asyncpg.connect(_raw_dsn())
    try:
        officer_id = await conn.fetchval(
            """
            INSERT INTO officers (firebase_uid, employee_id, employee_id_verified, full_name, state)
            VALUES ($1, $2, true, $3, $4)
            RETURNING id
            """,
            f"auto-assign-{employee_id}",
            employee_id,
            f"Officer {employee_id}",
            state,
        )
        await conn.execute(
            "UPDATE officers SET created_by=$1, updated_by=$1 WHERE id=$1", officer_id
        )
        return officer_id
    finally:
        await conn.close()


async def _load_officer_with_decoy_assignment(officer_id: int) -> int:
    """Attaches a throwaway business to `officer_id` so it counts as
    "already has one assignment" for a least-loaded comparison. Returns the
    decoy business id (owned by a decoy user) so the caller can clean it up.
    """
    conn = await asyncpg.connect(_raw_dsn())
    try:
        user_id = await conn.fetchval(
            """
            INSERT INTO users (firebase_uid, phone_e164, name)
            VALUES ($1, $2, 'Decoy Owner') RETURNING id
            """,
            f"auto-assign-decoy-{officer_id}",
            f"+9199990{officer_id:05d}",
        )
        await conn.execute("UPDATE users SET created_by=$1, updated_by=$1 WHERE id=$1", user_id)
        business_id = await conn.fetchval(
            """
            INSERT INTO businesses
                (user_id, name, segment, sector, tenure, staff_count,
                 is_new_business, years_in_operation, created_by, updated_by)
            VALUES ($1, 'Decoy Business', 'shg', 'dairy', 'under_1', 1, false, 0, $1, $1)
            RETURNING id
            """,
            user_id,
        )
        await conn.execute(
            """
            INSERT INTO officer_enterprise_assignments (officer_id, business_id, created_by, updated_by)
            VALUES ($1, $2, $1, $1)
            """,
            officer_id, business_id,
        )
        return business_id
    finally:
        await conn.close()


async def _assigned_officer_id(business_id: int) -> int | None:
    conn = await asyncpg.connect(_raw_dsn())
    try:
        return await conn.fetchval(
            "SELECT officer_id FROM officer_enterprise_assignments WHERE business_id=$1",
            business_id,
        )
    finally:
        await conn.close()


async def _cleanup(*, officer_ids: list[int], firebase_uid: str, decoy_business_ids: list[int] | None = None) -> None:
    conn = await asyncpg.connect(_raw_dsn())
    try:
        user_id = await conn.fetchval(
            "SELECT id FROM users WHERE firebase_uid=$1", firebase_uid
        )
        if user_id is not None:
            # businesses.id cascades to monthly_snapshots, health_scores,
            # forecasts, risk_alerts and officer_enterprise_assignments.
            await conn.execute("DELETE FROM businesses WHERE user_id=$1", user_id)
            await conn.execute("DELETE FROM users WHERE id=$1", user_id)
        for business_id in decoy_business_ids or []:
            decoy_owner_id = await conn.fetchval(
                "SELECT user_id FROM businesses WHERE id=$1", business_id
            )
            await conn.execute("DELETE FROM businesses WHERE id=$1", business_id)
            if decoy_owner_id is not None:
                await conn.execute("DELETE FROM users WHERE id=$1", decoy_owner_id)
        for officer_id in officer_ids:
            await conn.execute("DELETE FROM officers WHERE id=$1", officer_id)
    finally:
        await conn.close()


@pytest.fixture
def state_matched_officers():
    """Two officers, one in the owner's state ('Auto State'), one elsewhere —
    lets tests assert the state match wins over a same-load tie-break. The
    state is distinctive enough that no pre-existing officer in a shared dev
    database is expected to already have it.
    """
    matching_id = _run(_create_officer(employee_id="AUTO-MATCH", state="Auto State"))
    other_id = _run(_create_officer(employee_id="AUTO-OTHER", state="Other State"))
    yield matching_id, other_id
    # Business/user cleanup happens in the test's own `finally` block.


def test_new_business_is_auto_assigned_to_officer_in_same_state(client, state_matched_officers):
    matching_officer_id, other_officer_id = state_matched_officers
    headers = {"X-Debug-Firebase-Uid": "auto-owner-1"}
    try:
        me = client.patch("/api/v1/me", headers=headers, json={"state": "Auto State"})
        assert me.status_code == 200

        response = client.post("/api/v1/businesses", headers=headers, json=BUSINESS_PAYLOAD)
        assert response.status_code == 201
        business_id = response.json()["id"]

        assigned = _run(_assigned_officer_id(business_id))
        assert assigned == matching_officer_id
        assert assigned != other_officer_id
    finally:
        _run(
            _cleanup(
                officer_ids=[matching_officer_id, other_officer_id],
                firebase_uid="auto-owner-1",
            )
        )


def test_least_loaded_officer_wins_within_a_matched_state(client):
    """Two officers share a state; one already has a business. The
    freshly-created business must go to the officer with fewer, not the
    lower officer id — proves the load-balancing tie-break actually runs,
    independent of whatever else is in this shared dev database.
    """
    busy_officer_id = _run(_create_officer(employee_id="AUTO-BUSY", state="Balanced State"))
    free_officer_id = _run(_create_officer(employee_id="AUTO-FREE", state="Balanced State"))
    decoy_business_id = _run(_load_officer_with_decoy_assignment(busy_officer_id))
    headers = {"X-Debug-Firebase-Uid": "auto-owner-4"}
    try:
        me = client.patch("/api/v1/me", headers=headers, json={"state": "Balanced State"})
        assert me.status_code == 200

        response = client.post("/api/v1/businesses", headers=headers, json=BUSINESS_PAYLOAD)
        assert response.status_code == 201
        business_id = response.json()["id"]

        assert _run(_assigned_officer_id(business_id)) == free_officer_id
    finally:
        _run(
            _cleanup(
                officer_ids=[busy_officer_id, free_officer_id],
                firebase_uid="auto-owner-4",
                decoy_business_ids=[decoy_business_id],
            )
        )


def test_new_business_still_gets_assigned_when_no_officer_matches_the_state(client):
    """No officer is posted to the business owner's state — the fallback
    (least-loaded officer overall) must still pick *someone* rather than
    leaving the business unassigned. Which officer wins the global
    tie-break isn't asserted here, since other officers may already exist
    in this database outside this test's control.
    """
    officer_id = _run(_create_officer(employee_id="AUTO-FALLBACK", state="Officer State"))
    headers = {"X-Debug-Firebase-Uid": "auto-owner-2"}
    try:
        me = client.patch(
            "/api/v1/me", headers=headers, json={"state": "Nonexistent Owner State"}
        )
        assert me.status_code == 200

        response = client.post("/api/v1/businesses", headers=headers, json=BUSINESS_PAYLOAD)
        assert response.status_code == 201
        business_id = response.json()["id"]

        assert _run(_assigned_officer_id(business_id)) is not None
    finally:
        _run(_cleanup(officer_ids=[officer_id], firebase_uid="auto-owner-2"))
