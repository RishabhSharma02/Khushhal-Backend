HEADERS = {"X-Debug-Firebase-Uid": "test-officer-uid"}


def test_get_profile(client, seeded_officer):
    response = client.get("/api/officer/v1/profile", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["employee_id"] == "TEST-EMP-001"


def test_patch_profile_updates_and_persists(client, seeded_officer):
    response = client.patch("/api/officer/v1/profile", headers=HEADERS, json={"block": "New Block"})
    assert response.status_code == 200
    assert response.json()["block"] == "New Block"

    refetched = client.get("/api/officer/v1/profile", headers=HEADERS)
    assert refetched.json()["block"] == "New Block"


def test_get_profile_unauthorized_without_token(client):
    response = client.get("/api/officer/v1/profile")
    assert response.status_code == 401


def test_patch_profile_can_add_mobile_later(client, seeded_officer):
    response = client.patch(
        "/api/officer/v1/profile", headers=HEADERS, json={"mobile_e164": "+919888800001"}
    )
    assert response.status_code == 200
    assert response.json()["mobile_e164"] == "+919888800001"


def test_patch_profile_can_clear_mobile(client, seeded_officer):
    client.patch("/api/officer/v1/profile", headers=HEADERS, json={"mobile_e164": "+919888800001"})
    response = client.patch("/api/officer/v1/profile", headers=HEADERS, json={"mobile_e164": None})
    assert response.status_code == 200
    assert response.json()["mobile_e164"] is None
