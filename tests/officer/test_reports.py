HEADERS = {"X-Debug-Firebase-Uid": "test-officer-uid"}


def test_reports_summary_reflects_seeded_business(client, seeded_enterprise):
    response = client.get("/api/officer/v1/reports", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["average_health_score"] == 60
    assert body["flags_opened"] == 1
    assert len(body["sector_scores"]) == 1
    assert body["sector_scores"][0]["label"] == "Dairy"
    assert body["sector_scores"][0]["enterprise_count"] == 1
    assert body["app_adoption"]["total_enterprises"] == 1
    assert body["app_adoption"]["active_savings_plans"] == 1  # seeded user has savings_inr > 0


def test_reports_month_label_is_current_month(client, seeded_enterprise):
    from datetime import date

    response = client.get("/api/officer/v1/reports", headers=HEADERS)
    body = response.json()
    today = date.today()
    assert str(today.year) in body["month_label"]


def test_reports_unauthorized_without_token(client):
    response = client.get("/api/officer/v1/reports")
    assert response.status_code == 401


def test_reports_emis_on_time_is_none_with_zero_enterprises(client, seeded_officer):
    response = client.get("/api/officer/v1/reports", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["emis_on_time_percent"] is None
    assert body["emis_on_time_delta"] is None


def test_reports_emis_on_time_is_100_with_an_enterprise(client, seeded_enterprise):
    response = client.get("/api/officer/v1/reports", headers=HEADERS)
    body = response.json()
    assert body["emis_on_time_percent"] == 100
    assert body["emis_on_time_delta"] == 0
