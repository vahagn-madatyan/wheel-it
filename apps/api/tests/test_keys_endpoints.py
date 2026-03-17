"""Tests for key management endpoints (S02 T04).

All tests use mock_auth (bypasses JWT) and mock_db (AsyncMock asyncpg connection)
from conftest.py.  The encryption service runs with a real KEK via mock_encryption.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio

from apps.api.main import app
from apps.api.services.auth import get_current_user
from apps.api.tests.conftest import TEST_USER_ID


# ---------------------------------------------------------------------------
# Async client shared by all tests in this module
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(mock_auth, mock_db, mock_encryption):
    """Async client with auth + db + encryption mocked."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# POST /{provider} — store key
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_store_alpaca_key(client, mock_db):
    """POST /api/keys/alpaca stores an encrypted key and returns status."""
    resp = await client.post(
        "/api/keys/alpaca",
        json={"key_value": "AKTEST123", "key_name": "api_key"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "stored"
    assert body["provider"] == "alpaca"
    assert body["key_name"] == "api_key"

    # Verify db.execute was called with encrypted bytes, not plaintext
    mock_db.execute.assert_awaited_once()
    call_args = mock_db.execute.call_args[0]
    # Positional args: (sql, user_id, provider, key_name, enc_val, enc_dek, nonce, dek_nonce, is_paper)
    encrypted_value = call_args[4]
    encrypted_dek = call_args[5]
    nonce = call_args[6]
    dek_nonce = call_args[7]
    assert isinstance(encrypted_value, bytes), "encrypted_value must be bytes"
    assert isinstance(encrypted_dek, bytes), "encrypted_dek must be bytes"
    assert isinstance(nonce, bytes), "nonce must be bytes"
    assert isinstance(dek_nonce, bytes), "dek_nonce must be bytes"
    # Plaintext must NOT appear in stored values
    assert b"AKTEST123" not in encrypted_value


@pytest.mark.asyncio
async def test_store_alpaca_secret_key(client, mock_db):
    """POST /api/keys/alpaca accepts secret_key as key_name."""
    resp = await client.post(
        "/api/keys/alpaca",
        json={"key_value": "my-secret", "key_name": "secret_key", "is_paper": True},
    )
    assert resp.status_code == 200
    assert resp.json()["key_name"] == "secret_key"


@pytest.mark.asyncio
async def test_store_finnhub_key(client, mock_db):
    """POST /api/keys/finnhub stores a Finnhub key."""
    resp = await client.post(
        "/api/keys/finnhub",
        json={"key_value": "fh-key-123", "key_name": "api_key"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "stored"
    assert body["provider"] == "finnhub"


@pytest.mark.asyncio
async def test_store_invalid_provider(client):
    """POST /api/keys/invalid returns 422."""
    resp = await client.post(
        "/api/keys/invalid",
        json={"key_value": "x", "key_name": "api_key"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_store_invalid_key_name(client):
    """POST /api/keys/finnhub with key_name=secret_key returns 422."""
    resp = await client.post(
        "/api/keys/finnhub",
        json={"key_value": "x", "key_name": "secret_key"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /status — list providers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_key_status(client, mock_db):
    """GET /api/keys/status returns provider list without exposing key values."""
    # Simulate DB returning two alpaca keys
    mock_db.fetch.return_value = [
        {"provider": "alpaca", "key_name": "api_key", "is_paper": True},
        {"provider": "alpaca", "key_name": "secret_key", "is_paper": True},
    ]
    resp = await client.get("/api/keys/status")
    assert resp.status_code == 200
    body = resp.json()
    providers = body["providers"]
    assert len(providers) == 1
    assert providers[0]["provider"] == "alpaca"
    assert providers[0]["connected"] is True
    assert sorted(providers[0]["key_names"]) == ["api_key", "secret_key"]
    # key_value must NEVER appear in response
    raw = resp.text
    assert "AKTEST" not in raw
    assert "key_value" not in raw


@pytest.mark.asyncio
async def test_get_key_status_empty(client, mock_db):
    """GET /api/keys/status with no keys returns empty providers list."""
    mock_db.fetch.return_value = []
    resp = await client.get("/api/keys/status")
    assert resp.status_code == 200
    assert resp.json()["providers"] == []


# ---------------------------------------------------------------------------
# DELETE /{provider} — remove keys
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_keys(client, mock_db):
    """DELETE /api/keys/alpaca removes keys and returns status."""
    resp = await client.delete("/api/keys/alpaca")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "deleted"
    assert body["provider"] == "alpaca"
    mock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_invalid_provider(client):
    """DELETE /api/keys/invalid returns 422."""
    resp = await client.delete("/api/keys/invalid")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /{provider}/verify — test connectivity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_alpaca_keys_success(client, mock_db, mock_encryption):
    """POST /api/keys/alpaca/verify returns valid=True on successful get_account."""
    from apps.api.services.encryption import encrypt_value

    enc_api = encrypt_value("AKTEST123")
    enc_secret = encrypt_value("SKTEST456")

    mock_db.fetch.return_value = [
        {
            "key_name": "api_key",
            "encrypted_value": enc_api[0],
            "encrypted_dek": enc_api[1],
            "nonce": enc_api[2],
            "dek_nonce": enc_api[3],
            "is_paper": True,
        },
        {
            "key_name": "secret_key",
            "encrypted_value": enc_secret[0],
            "encrypted_dek": enc_secret[1],
            "nonce": enc_secret[2],
            "dek_nonce": enc_secret[3],
            "is_paper": True,
        },
    ]

    with patch("apps.api.routers.keys.asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_thread.return_value = None  # get_account succeeds
        resp = await client.post("/api/keys/alpaca/verify")

    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "alpaca"
    assert body["valid"] is True
    assert body["error"] is None


@pytest.mark.asyncio
async def test_verify_alpaca_keys_failure(client, mock_db, mock_encryption):
    """POST /api/keys/alpaca/verify returns valid=False when get_account fails."""
    from apps.api.services.encryption import encrypt_value

    enc_api = encrypt_value("AKBAD")
    enc_secret = encrypt_value("SKBAD")

    mock_db.fetch.return_value = [
        {
            "key_name": "api_key",
            "encrypted_value": enc_api[0],
            "encrypted_dek": enc_api[1],
            "nonce": enc_api[2],
            "dek_nonce": enc_api[3],
            "is_paper": True,
        },
        {
            "key_name": "secret_key",
            "encrypted_value": enc_secret[0],
            "encrypted_dek": enc_secret[1],
            "nonce": enc_secret[2],
            "dek_nonce": enc_secret[3],
            "is_paper": True,
        },
    ]

    with patch("apps.api.routers.keys.asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_thread.side_effect = Exception("API key is invalid")
        resp = await client.post("/api/keys/alpaca/verify")

    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False
    assert "invalid" in body["error"].lower()


@pytest.mark.asyncio
async def test_verify_no_keys_stored(client, mock_db):
    """POST /api/keys/alpaca/verify returns valid=False when no keys exist."""
    mock_db.fetch.return_value = []
    resp = await client.post("/api/keys/alpaca/verify")
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False
    assert "no keys" in body["error"].lower()


@pytest.mark.asyncio
async def test_verify_invalid_provider(client):
    """POST /api/keys/invalid/verify returns 422."""
    resp = await client.post("/api/keys/invalid/verify")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Auth enforcement — unauthenticated requests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(mock_db, mock_encryption):
    """Requests without auth token are rejected with 403."""
    # Do NOT use mock_auth — we want the real auth dependency
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/keys/status")
    assert resp.status_code in (401, 403)
