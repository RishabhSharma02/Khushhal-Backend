HEADERS = {"X-Debug-Firebase-Uid": "test-officer-uid"}


def test_dashboard_reflects_current_month_score(client, seeded_enterprise):
    response = client.get("/api/officer/v1/dashboard", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert len(body["average_score_history"]) == 6
    assert body["average_score_history"][-1] == 60  # seeded health_score.score


def test_dashboard_counts_open_flag(client, seeded_enterprise):
    response = client.get("/api/officer/v1/dashboard", headers=HEADERS)
    body = response.json()
    assert body["open_flag_count"] == 1
    assert body["open_flag_delta"] == 1  # raised within last 30 days, unresolved


def test_dashboard_unauthorized_without_token(client):
    response = client.get("/api/officer/v1/dashboard")
    assert response.status_code == 401


def test_dashboard_emis_on_time_is_none_with_zero_enterprises(client, seeded_officer):
    response = client.get("/api/officer/v1/dashboard", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["emis_on_time_percent"] is None
    assert body["emis_on_time_delta"] is None


def test_dashboard_emis_on_time_is_100_with_an_enterprise(client, seeded_enterprise):
    response = client.get("/api/officer/v1/dashboard", headers=HEADERS)
    body = response.json()
    assert body["emis_on_time_percent"] == 100
    assert body["emis_on_time_delta"] == 0
