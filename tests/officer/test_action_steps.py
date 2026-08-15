HEADERS = {"X-Debug-Firebase-Uid": "test-officer-uid"}


def _base(business_id: int) -> str:
    return f"/api/officer/v1/enterprises/{business_id}/action-steps"


def test_create_and_list_action_steps(client, seeded_enterprise):
    created = client.post(
        _base(seeded_enterprise), headers=HEADERS,
        json={"title": "Step one", "detail": "do it", "impact": "high"},
    )
    assert created.status_code == 201
    assert created.json()["ordinal"] == 1

    listed = client.get(_base(seeded_enterprise), headers=HEADERS)
    assert listed.status_code == 200
    assert [s["title"] for s in listed.json()] == ["Step one"]


def test_update_action_step(client, seeded_enterprise):
    created = client.post(
        _base(seeded_enterprise), headers=HEADERS,
        json={"title": "Original", "detail": "d", "impact": "low"},
    ).json()

    updated = client.patch(
        f"{_base(seeded_enterprise)}/{created['id']}", headers=HEADERS,
        json={"title": "Updated", "detail": "d2", "impact": "high"},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["title"] == "Updated"
    assert body["impact"] == "high"
    assert body["ordinal"] == created["ordinal"]  # order preserved on edit


def test_delete_action_step_renumbers_remaining(client, seeded_enterprise):
    first = client.post(
        _base(seeded_enterprise), headers=HEADERS,
        json={"title": "First", "detail": "", "impact": "low"},
    ).json()
    second = client.post(
        _base(seeded_enterprise), headers=HEADERS,
        json={"title": "Second", "detail": "", "impact": "low"},
    ).json()
    assert second["ordinal"] == 2

    deleted = client.delete(f"{_base(seeded_enterprise)}/{first['id']}", headers=HEADERS)
    assert deleted.status_code == 204

    remaining = client.get(_base(seeded_enterprise), headers=HEADERS).json()
    assert len(remaining) == 1
    assert remaining[0]["id"] == second["id"]
    assert remaining[0]["ordinal"] == 1


def test_action_steps_not_found_for_unassigned_business(client, seeded_officer):
    response = client.get(_base(999999999), headers=HEADERS)
    assert response.status_code == 404


def test_action_steps_unauthorized_without_token(client, seeded_enterprise):
    response = client.get(_base(seeded_enterprise))
    assert response.status_code == 401


def test_send_action_plan_publishes_field_officer_plan_actions(client, seeded_enterprise):
    import asyncio

    import asyncpg

    from tests.officer.conftest import _raw_dsn

    client.post(
        _base(seeded_enterprise), headers=HEADERS,
        json={"title": "Talk to owner", "detail": "about savings", "impact": "high"},
    )

    response = client.post(f"{_base(seeded_enterprise)}/send", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["steps_sent"] == 1
    alert_id = body["alert_id"]

    async def _fetch():
        conn = await asyncpg.connect(_raw_dsn())
        try:
            return await conn.fetch(
                "SELECT role, label_en, ordinal FROM plan_actions WHERE alert_id = $1", alert_id
            )
        finally:
            await conn.close()

    rows = asyncio.run(_fetch())
    assert len(rows) == 1
    assert rows[0]["role"] == "field_officer"
    assert rows[0]["label_en"] == "Talk to owner: about savings"


def test_send_action_plan_replaces_previous_send(client, seeded_enterprise):
    client.post(
        _base(seeded_enterprise), headers=HEADERS,
        json={"title": "First plan", "detail": "", "impact": "low"},
    )
    first = client.post(f"{_base(seeded_enterprise)}/send", headers=HEADERS).json()
    assert first["steps_sent"] == 1

    client.post(
        _base(seeded_enterprise), headers=HEADERS,
        json={"title": "Second step", "detail": "", "impact": "low"},
    )
    second = client.post(f"{_base(seeded_enterprise)}/send", headers=HEADERS).json()
    assert second["steps_sent"] == 2  # replaces, not appends onto the first send


def test_send_action_plan_conflict_when_no_open_alert(client, seeded_enterprise):
    import asyncio

    import asyncpg

    from tests.officer.conftest import _raw_dsn

    async def _resolve():
        conn = await asyncpg.connect(_raw_dsn())
        try:
            await conn.execute(
                "UPDATE risk_alerts SET resolved_at = now() WHERE business_id = $1",
                seeded_enterprise,
            )
        finally:
            await conn.close()

    asyncio.run(_resolve())

    response = client.post(f"{_base(seeded_enterprise)}/send", headers=HEADERS)
    assert response.status_code == 409
