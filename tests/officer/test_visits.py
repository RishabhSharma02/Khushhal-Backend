HEADERS = {"X-Debug-Firebase-Uid": "test-officer-uid"}


def test_create_and_list_visit(client, seeded_enterprise):
    created = client.post(
        "/api/officer/v1/visits", headers=HEADERS,
        json={
            "business_id": seeded_enterprise,
            "date": "2026-08-10T09:30:00Z",
            "agenda": "Checked stock",
            "risk_level": "watch",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["enterprise_id"] == str(seeded_enterprise)
    assert body["enterprise_name"] == "Test Dairy"
    assert body["status"] == "done"
    assert body["risk_level"] == "watch"

    listed = client.get("/api/officer/v1/visits", headers=HEADERS)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_create_visit_without_risk_level(client, seeded_enterprise):
    created = client.post(
        "/api/officer/v1/visits", headers=HEADERS,
        json={"business_id": seeded_enterprise, "date": "2026-08-10T09:30:00Z", "agenda": "Quick check"},
    )
    assert created.status_code == 201
    assert created.json()["risk_level"] is None


def test_create_visit_not_found_for_unassigned_business(client, seeded_officer):
    response = client.post(
        "/api/officer/v1/visits", headers=HEADERS,
        json={"business_id": 999999999, "date": "2026-08-10T09:30:00Z", "agenda": "x"},
    )
    assert response.status_code == 404


def test_visits_unauthorized_without_token(client):
    response = client.get("/api/officer/v1/visits")
    assert response.status_code == 401
