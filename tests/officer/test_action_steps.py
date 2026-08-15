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
