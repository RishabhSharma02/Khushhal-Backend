HEADERS = {"X-Debug-Firebase-Uid": "test-officer-uid"}


def test_coverage_reflects_assigned_enterprise(client, seeded_enterprise):
    response = client.get("/api/officer/v1/profile/coverage", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["enterprise_count"] == 1
    assert body["village_count"] == 1
    assert body["visits_this_month"] == 0
    assert body["flags_resolved_last_30_days"] == 0


def test_coverage_zero_for_officer_with_no_assignments(client, seeded_officer):
    response = client.get("/api/officer/v1/profile/coverage", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "enterprise_count": 0,
        "village_count": 0,
        "visits_this_month": 0,
        "flags_resolved_last_30_days": 0,
    }


def test_coverage_unauthorized_without_token(client):
    response = client.get("/api/officer/v1/profile/coverage")
    assert response.status_code == 401
