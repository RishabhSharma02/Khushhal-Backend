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
