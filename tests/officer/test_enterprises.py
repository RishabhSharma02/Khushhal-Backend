HEADERS = {"X-Debug-Firebase-Uid": "test-officer-uid"}


def test_list_enterprises_returns_assigned_business(client, seeded_enterprise):
    response = client.get("/api/officer/v1/enterprises", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(seeded_enterprise)
    assert body[0]["name"] == "Test Dairy"
    assert body[0]["risk_level"] == "watch"  # amber band
    assert body[0]["financials"]["cash_on_hand_inr"] == 3000  # 3 x 1000 in


def test_get_enterprise_detail(client, seeded_enterprise):
    response = client.get(f"/api/officer/v1/enterprises/{seeded_enterprise}", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["contact"]["name"] == "Test Owner"
    assert body["flag_summary"] == "Test flag driver"
    assert body["financials"]["savings_inr"] == 5000
    assert body["financials"]["loan_left_inr"] == 2000


def test_get_enterprise_not_found_for_unassigned_business(client, seeded_officer):
    response = client.get("/api/officer/v1/enterprises/999999999", headers=HEADERS)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_cash_flow_includes_actual_month(client, seeded_enterprise):
    response = client.get(f"/api/officer/v1/enterprises/{seeded_enterprise}/cash-flow", headers=HEADERS)
    assert response.status_code == 200
    months = response.json()
    assert len(months) >= 1
    actual = [m for m in months if not m["is_forecast"]]
    assert actual[0]["money_in_inr"] == 10000
    assert actual[0]["money_out_inr"] == 8000


def test_data_quality(client, seeded_enterprise):
    response = client.get(f"/api/officer/v1/enterprises/{seeded_enterprise}/data-quality", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["entry_streak_days_per_week"] == 3
    assert body["forecast_confidence_percent"] == 50  # amber band -> p_amber 0.5


def test_enterprises_unauthorized_without_token(client):
    response = client.get("/api/officer/v1/enterprises")
    assert response.status_code == 401
