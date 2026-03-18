"""Tests for screening submit/poll endpoints.

Uses mock auth + mock key retrieval instead of raw Alpaca keys.
Shared fixtures (SAMPLE_PUT, SAMPLE_CALL, mock_auth, etc.) live in conftest.py.
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.schemas import PutResultSchema
from apps.api.tests.conftest import SAMPLE_CALL, SAMPLE_PUT


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


MOCK_PUT_RESULTS = [SAMPLE_PUT]
MOCK_CALL_RESULTS = [SAMPLE_CALL]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_key_retrieval():
    """Mock retrieve_alpaca_keys in the screen router to return test credentials."""
    with patch(
        "apps.api.routers.screen.retrieve_alpaca_keys",
        return_value=("test-key", "test-secret", True),
    ) as m:
        yield m


# ---------------------------------------------------------------------------
# PUT screening
# ---------------------------------------------------------------------------


@patch("apps.api.routers.screen.screen_puts", return_value=MOCK_PUT_RESULTS)
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_put_screen_submit_returns_202(
    mock_clients, mock_screen, client, mock_auth, mock_db, mock_key_retrieval, auth_headers,
):
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())
    resp = client.post(
        "/api/screen/puts",
        json={"symbols": ["AAPL"], "buying_power": 50000.0},
        headers=auth_headers,
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "run_id" in data
    assert data["status"] == "pending"


@patch("apps.api.routers.screen.screen_puts", return_value=MOCK_PUT_RESULTS)
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_put_screen_poll_returns_completed(
    mock_clients, mock_screen, client, mock_auth, mock_db, mock_key_retrieval, auth_headers,
):
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())
    resp = client.post(
        "/api/screen/puts",
        json={"symbols": ["AAPL"], "buying_power": 50000.0},
        headers=auth_headers,
    )
    run_id = resp.json()["run_id"]

    time.sleep(0.5)

    poll = client.get(f"/api/screen/runs/{run_id}", headers=auth_headers)
    assert poll.status_code == 200
    data = poll.json()
    assert data["status"] == "completed"
    assert data["run_type"] == "put_screen"
    assert len(data["results"]) == 1
    assert data["results"][0]["underlying"] == "AAPL"
    assert data["results"][0]["annualized_return"] == 21.35


# ---------------------------------------------------------------------------
# CALL screening
# ---------------------------------------------------------------------------


@patch("apps.api.routers.screen.screen_calls", return_value=MOCK_CALL_RESULTS)
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_call_screen_submit_returns_202(
    mock_clients, mock_screen, client, mock_auth, mock_db, mock_key_retrieval, auth_headers,
):
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())
    resp = client.post(
        "/api/screen/calls",
        json={"symbol": "AAPL", "cost_basis": 195.0},
        headers=auth_headers,
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "run_id" in data
    assert data["status"] == "pending"


@patch("apps.api.routers.screen.screen_calls", return_value=MOCK_CALL_RESULTS)
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_call_screen_poll_returns_completed(
    mock_clients, mock_screen, client, mock_auth, mock_db, mock_key_retrieval, auth_headers,
):
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())
    resp = client.post(
        "/api/screen/calls",
        json={"symbol": "AAPL", "cost_basis": 195.0},
        headers=auth_headers,
    )
    run_id = resp.json()["run_id"]

    time.sleep(0.5)

    poll = client.get(f"/api/screen/runs/{run_id}", headers=auth_headers)
    assert poll.status_code == 200
    data = poll.json()
    assert data["status"] == "completed"
    assert data["run_type"] == "call_screen"
    assert len(data["results"]) == 1
    assert data["results"][0]["cost_basis"] == 195.0


# ---------------------------------------------------------------------------
# Poll: unknown run_id
# ---------------------------------------------------------------------------


def test_unknown_run_id_returns_404(client, mock_auth, auth_headers):
    resp = client.get("/api/screen/runs/nonexistent", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Status progression: pending → running → completed
# ---------------------------------------------------------------------------


@patch("apps.api.routers.screen.screen_puts")
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_status_progression(
    mock_clients, mock_screen, client, mock_auth, mock_db, mock_key_retrieval, auth_headers,
):
    """Submit returns pending; after background work completes, poll returns completed."""

    def slow_screen(*args, **kwargs):
        time.sleep(0.3)
        return MOCK_PUT_RESULTS

    mock_screen.side_effect = slow_screen
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())

    resp = client.post(
        "/api/screen/puts",
        json={"symbols": ["AAPL"], "buying_power": 50000.0},
        headers=auth_headers,
    )
    run_id = resp.json()["run_id"]
    assert resp.json()["status"] == "pending"

    # After completion
    time.sleep(1.0)
    poll = client.get(f"/api/screen/runs/{run_id}", headers=auth_headers)
    assert poll.json()["status"] == "completed"


# ---------------------------------------------------------------------------
# Failed screening captures error
# ---------------------------------------------------------------------------


@patch("apps.api.routers.screen.screen_puts", side_effect=RuntimeError("API timeout"))
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_failed_screen_captures_error(
    mock_clients, mock_screen, client, mock_auth, mock_db, mock_key_retrieval, auth_headers,
):
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())
    resp = client.post(
        "/api/screen/puts",
        json={"symbols": ["AAPL"], "buying_power": 50000.0},
        headers=auth_headers,
    )
    run_id = resp.json()["run_id"]

    time.sleep(0.5)

    poll = client.get(f"/api/screen/runs/{run_id}", headers=auth_headers)
    data = poll.json()
    assert data["status"] == "failed"
    assert "API timeout" in data["error"]


# ---------------------------------------------------------------------------
# Invalid preset returns 400
# ---------------------------------------------------------------------------


@patch("apps.api.routers.screen.create_alpaca_clients")
def test_invalid_preset_returns_400(
    mock_clients, client, mock_auth, mock_db, mock_key_retrieval, auth_headers,
):
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())
    resp = client.post(
        "/api/screen/puts",
        json={"symbols": ["AAPL"], "buying_power": 50000.0, "preset": "yolo"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Pending run poll (immediate poll before background task advances)
# ---------------------------------------------------------------------------


@patch("apps.api.routers.screen.screen_puts")
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_poll_pending_run(
    mock_clients, mock_screen, client, mock_auth, mock_db, mock_key_retrieval, auth_headers,
):
    """Immediate poll after submit should return pending or running — not completed."""
    import threading

    def blocked_screen(*args, **kwargs):
        e = threading.Event()
        e.wait(5)
        return MOCK_PUT_RESULTS

    mock_screen.side_effect = blocked_screen
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())

    resp = client.post(
        "/api/screen/puts",
        json={"symbols": ["AAPL"], "buying_power": 50000.0},
        headers=auth_headers,
    )
    run_id = resp.json()["run_id"]

    poll = client.get(f"/api/screen/runs/{run_id}", headers=auth_headers)
    assert poll.status_code == 200
    assert poll.json()["status"] in ("pending", "running")


# ---------------------------------------------------------------------------
# Completed call run — dedicated test
# ---------------------------------------------------------------------------


@patch("apps.api.routers.screen.screen_calls", return_value=MOCK_CALL_RESULTS)
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_poll_completed_call_run(
    mock_clients, mock_screen, client, mock_auth, mock_db, mock_key_retrieval, auth_headers,
):
    """Poll a completed call screen returns results with cost_basis field."""
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())
    resp = client.post(
        "/api/screen/calls",
        json={"symbol": "AAPL", "cost_basis": 195.0},
        headers=auth_headers,
    )
    run_id = resp.json()["run_id"]

    time.sleep(0.5)

    poll = client.get(f"/api/screen/runs/{run_id}", headers=auth_headers)
    data = poll.json()
    assert data["status"] == "completed"
    assert data["run_type"] == "call_screen"
    assert len(data["results"]) == 1
    result = data["results"][0]
    assert result["cost_basis"] == 195.0
    assert result["underlying"] == "AAPL"
    assert result["strike"] == 210.0


# ---------------------------------------------------------------------------
# Put results match PutResultSchema fields
# ---------------------------------------------------------------------------


@patch("apps.api.routers.screen.screen_puts", return_value=MOCK_PUT_RESULTS)
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_put_results_match_schema(
    mock_clients, mock_screen, client, mock_auth, mock_db, mock_key_retrieval, auth_headers,
):
    """Completed put results contain every field from PutResultSchema."""
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())
    resp = client.post(
        "/api/screen/puts",
        json={"symbols": ["AAPL"], "buying_power": 50000.0},
        headers=auth_headers,
    )
    run_id = resp.json()["run_id"]

    time.sleep(0.5)

    poll = client.get(f"/api/screen/runs/{run_id}", headers=auth_headers)
    data = poll.json()
    assert data["status"] == "completed"

    result = data["results"][0]
    expected_fields = set(PutResultSchema.model_fields.keys())
    assert set(result.keys()) == expected_fields

    assert result["symbol"] == "AAPL250418P00200000"
    assert result["underlying"] == "AAPL"
    assert result["strike"] == 200.0
    assert result["dte"] == 30
    assert result["premium"] == 3.50
    assert result["delta"] == -0.25
    assert result["oi"] == 1500
    assert result["spread"] == 0.03
    assert result["annualized_return"] == 21.35


# ---------------------------------------------------------------------------
# Auth error paths
# ---------------------------------------------------------------------------


def test_put_screen_missing_auth_returns_401(client):
    """Request without Authorization header returns 401."""
    resp = client.post(
        "/api/screen/puts",
        json={"symbols": ["AAPL"], "buying_power": 50000.0},
    )
    assert resp.status_code == 401


def test_poll_missing_auth_returns_401(client):
    """Poll endpoint without auth returns 401."""
    resp = client.get("/api/screen/runs/some-run-id")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Missing stored keys returns 400
# ---------------------------------------------------------------------------


@patch("apps.api.routers.screen.retrieve_alpaca_keys")
def test_put_screen_missing_keys_returns_400(
    mock_retrieve, client, mock_auth, mock_db, auth_headers,
):
    """When no keys are stored in DB, returns 400 with descriptive message."""
    from fastapi import HTTPException

    mock_retrieve.side_effect = HTTPException(
        status_code=400,
        detail="Alpaca API keys not configured. Add keys in Settings.",
    )
    resp = client.post(
        "/api/screen/puts",
        json={"symbols": ["AAPL"], "buying_power": 50000.0},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "not configured" in resp.json()["detail"]
