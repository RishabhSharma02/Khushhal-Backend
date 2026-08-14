import asyncio

import asyncpg

from tests.officer.conftest import _raw_dsn

HEADERS = {"X-Debug-Firebase-Uid": "test-register-uid", "X-Debug-Email": "register@test.com"}
PAYLOAD = {"employee_id": "TEST-REG-001", "full_name": "New Officer", "mobile_e164": "+919000000001"}


def _cleanup(firebase_uid: str) -> None:
    async def _run() -> None:
        conn = await asyncpg.connect(_raw_dsn())
        try:
            await conn.execute("DELETE FROM officers WHERE firebase_uid = $1", firebase_uid)
        finally:
            await conn.close()

    asyncio.run(_run())


def test_register_creates_officer(client):
    try:
        response = client.post("/api/officer/v1/auth/register", headers=HEADERS, json=PAYLOAD)
        assert response.status_code == 200
        body = response.json()["officer"]
        assert body["employee_id"] == "TEST-REG-001"
        assert body["employee_id_verified"] is False
        assert body["email"] == "register@test.com"
    finally:
        _cleanup("test-register-uid")


def test_register_then_session_signs_in(client):
    try:
        client.post("/api/officer/v1/auth/register", headers=HEADERS, json=PAYLOAD)
        response = client.post(
            "/api/officer/v1/auth/session", headers={"X-Debug-Firebase-Uid": "test-register-uid"}
        )
        assert response.status_code == 200
        assert response.json()["officer"]["employee_id"] == "TEST-REG-001"
    finally:
        _cleanup("test-register-uid")


def test_register_is_idempotent_for_same_uid(client):
    try:
        first = client.post("/api/officer/v1/auth/register", headers=HEADERS, json=PAYLOAD)
        second = client.post("/api/officer/v1/auth/register", headers=HEADERS, json=PAYLOAD)
        assert first.json()["officer"]["id"] == second.json()["officer"]["id"]
    finally:
        _cleanup("test-register-uid")


def test_register_duplicate_employee_id_conflicts(client):
    try:
        client.post("/api/officer/v1/auth/register", headers=HEADERS, json=PAYLOAD)
        other_headers = {"X-Debug-Firebase-Uid": "test-register-uid-2"}
        response = client.post(
            "/api/officer/v1/auth/register",
            headers=other_headers,
            json={**PAYLOAD, "mobile_e164": "+919000000002"},
        )
        assert response.status_code == 409
    finally:
        _cleanup("test-register-uid")
        _cleanup("test-register-uid-2")


def test_register_unauthorized_without_token(client):
    response = client.post("/api/officer/v1/auth/register", json=PAYLOAD)
    assert response.status_code == 401


def test_register_without_mobile_succeeds(client):
    payload_no_mobile = {"employee_id": "TEST-REG-001", "full_name": "New Officer"}
    try:
        response = client.post(
            "/api/officer/v1/auth/register", headers=HEADERS, json=payload_no_mobile
        )
        assert response.status_code == 200
        assert response.json()["officer"]["mobile_e164"] is None
    finally:
        _cleanup("test-register-uid")
