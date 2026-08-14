HEADERS = {"X-Debug-Firebase-Uid": "test-officer-uid"}


def _base(business_id: int) -> str:
    return f"/api/officer/v1/enterprises/{business_id}/contact-log"


def test_create_and_list_contact_log(client, seeded_enterprise):
    created = client.post(
        _base(seeded_enterprise), headers=HEADERS,
        json={"occurred_at": "2026-07-28T09:30:00Z", "kind": "visit", "note": "checked stock"},
    )
    assert created.status_code == 201
    assert created.json()["kind"] == "visit"

    listed = client.get(_base(seeded_enterprise), headers=HEADERS)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["note"] == "checked stock"


def test_contact_log_newest_first(client, seeded_enterprise):
    client.post(
        _base(seeded_enterprise), headers=HEADERS,
        json={"occurred_at": "2026-06-01T09:00:00Z", "kind": "call", "note": "older"},
    )
    client.post(
        _base(seeded_enterprise), headers=HEADERS,
        json={"occurred_at": "2026-07-15T09:00:00Z", "kind": "visit", "note": "newer"},
    )
    listed = client.get(_base(seeded_enterprise), headers=HEADERS).json()
    assert [e["note"] for e in listed] == ["newer", "older"]


def test_contact_log_not_found_for_unassigned_business(client, seeded_officer):
    response = client.get(_base(999999999), headers=HEADERS)
    assert response.status_code == 404


def test_contact_log_unauthorized_without_token(client, seeded_enterprise):
    response = client.get(_base(seeded_enterprise))
    assert response.status_code == 401
