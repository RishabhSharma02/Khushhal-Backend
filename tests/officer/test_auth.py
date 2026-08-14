def test_session_returns_officer_for_known_uid(client, seeded_officer):
    response = client.post(
        "/api/officer/v1/auth/session", headers={"X-Debug-Firebase-Uid": "test-officer-uid"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["officer"]["employee_id"] == "TEST-EMP-001"
    assert body["officer"]["full_name"] == "Test Officer"


def test_session_forbidden_for_unregistered_uid(client):
    response = client.post(
        "/api/officer/v1/auth/session", headers={"X-Debug-Firebase-Uid": "no-such-officer"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_session_unauthorized_without_token(client):
    response = client.post("/api/officer/v1/auth/session")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
