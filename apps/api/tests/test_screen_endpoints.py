"""Tests for screening submit/poll endpoints.

Uses TestClient with mocked screener functions to avoid real Alpaca calls.
Shared fixtures (ALPACA_KEYS, SAMPLE_PUT, SAMPLE_CALL, etc.) live in conftest.py.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.schemas import PutResultSchema
from apps.api.tests.conftest import ALPACA_KEYS, SAMPLE_CALL, SAMPLE_PUT
from screener.call_screener import CallRecommendation
from screener.put_screener import PutRecommendation


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


MOCK_PUT_RESULTS = [SAMPLE_PUT]


@patch("apps.api.routers.screen.screen_puts", return_value=MOCK_PUT_RESULTS)
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_put_screen_submit_returns_202(mock_clients, mock_screen, client):
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())
    resp = client.post("/api/screen/puts", json={
        **ALPACA_KEYS,
        "symbols": ["AAPL"],
        "buying_power": 50000.0,
    })
    assert resp.status_code == 202
    data = resp.json()
    assert "run_id" in data
    assert data["status"] == "pending"


@patch("apps.api.routers.screen.screen_puts", return_value=MOCK_PUT_RESULTS)
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_put_screen_poll_returns_completed(mock_clients, mock_screen, client):
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())
    resp = client.post("/api/screen/puts", json={
        **ALPACA_KEYS,
        "symbols": ["AAPL"],
        "buying_power": 50000.0,
    })
    run_id = resp.json()["run_id"]

    # Give background task time to complete
    import time
    time.sleep(0.5)

    poll = client.get(f"/api/screen/runs/{run_id}")
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

MOCK_CALL_RESULTS = [SAMPLE_CALL]


@patch("apps.api.routers.screen.screen_calls", return_value=MOCK_CALL_RESULTS)
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_call_screen_submit_returns_202(mock_clients, mock_screen, client):
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())
    resp = client.post("/api/screen/calls", json={
        **ALPACA_KEYS,
        "symbol": "AAPL",
        "cost_basis": 195.0,
    })
    assert resp.status_code == 202
    data = resp.json()
    assert "run_id" in data
    assert data["status"] == "pending"


@patch("apps.api.routers.screen.screen_calls", return_value=MOCK_CALL_RESULTS)
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_call_screen_poll_returns_completed(mock_clients, mock_screen, client):
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())
    resp = client.post("/api/screen/calls", json={
        **ALPACA_KEYS,
        "symbol": "AAPL",
        "cost_basis": 195.0,
    })
    run_id = resp.json()["run_id"]

    import time
    time.sleep(0.5)

    poll = client.get(f"/api/screen/runs/{run_id}")
    assert poll.status_code == 200
    data = poll.json()
    assert data["status"] == "completed"
    assert data["run_type"] == "call_screen"
    assert len(data["results"]) == 1
    assert data["results"][0]["cost_basis"] == 195.0


# ---------------------------------------------------------------------------
# Poll: unknown run_id
# ---------------------------------------------------------------------------


def test_unknown_run_id_returns_404(client):
    resp = client.get("/api/screen/runs/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Status progression: pending → running → completed
# ---------------------------------------------------------------------------


@patch("apps.api.routers.screen.screen_puts")
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_status_progression(mock_clients, mock_screen, client):
    """Submit returns pending; after background work completes, poll returns completed."""
    import time

    # Make screen_puts block briefly so we can observe pending/running
    def slow_screen(*args, **kwargs):
        time.sleep(0.3)
        return MOCK_PUT_RESULTS

    mock_screen.side_effect = slow_screen
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())

    resp = client.post("/api/screen/puts", json={
        **ALPACA_KEYS,
        "symbols": ["AAPL"],
        "buying_power": 50000.0,
    })
    run_id = resp.json()["run_id"]
    assert resp.json()["status"] == "pending"

    # After completion
    time.sleep(1.0)
    poll = client.get(f"/api/screen/runs/{run_id}")
    assert poll.json()["status"] == "completed"


# ---------------------------------------------------------------------------
# Failed screening captures error
# ---------------------------------------------------------------------------


@patch("apps.api.routers.screen.screen_puts", side_effect=RuntimeError("API timeout"))
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_failed_screen_captures_error(mock_clients, mock_screen, client):
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())
    resp = client.post("/api/screen/puts", json={
        **ALPACA_KEYS,
        "symbols": ["AAPL"],
        "buying_power": 50000.0,
    })
    run_id = resp.json()["run_id"]

    import time
    time.sleep(0.5)

    poll = client.get(f"/api/screen/runs/{run_id}")
    data = poll.json()
    assert data["status"] == "failed"
    assert "API timeout" in data["error"]


# ---------------------------------------------------------------------------
# Invalid preset returns 400
# ---------------------------------------------------------------------------


@patch("apps.api.routers.screen.create_alpaca_clients")
def test_invalid_preset_returns_400(mock_clients, client):
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())
    resp = client.post("/api/screen/puts", json={
        **ALPACA_KEYS,
        "symbols": ["AAPL"],
        "buying_power": 50000.0,
        "preset": "yolo",
    })
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Pending run poll (immediate poll before background task advances)
# ---------------------------------------------------------------------------


@patch("apps.api.routers.screen.screen_puts")
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_poll_pending_run(mock_clients, mock_screen, client):
    """Immediate poll after submit should return pending or running — not completed."""
    event = asyncio.Event()

    def blocked_screen(*args, **kwargs):
        """Block until event is set so status stays pending/running."""
        import threading
        e = threading.Event()
        e.wait(5)  # Will not be set — we just poll before it completes
        return MOCK_PUT_RESULTS

    mock_screen.side_effect = blocked_screen
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())

    resp = client.post("/api/screen/puts", json={
        **ALPACA_KEYS,
        "symbols": ["AAPL"],
        "buying_power": 50000.0,
    })
    run_id = resp.json()["run_id"]

    # Poll immediately — should be pending or running
    poll = client.get(f"/api/screen/runs/{run_id}")
    assert poll.status_code == 200
    assert poll.json()["status"] in ("pending", "running")


# ---------------------------------------------------------------------------
# Completed call run — dedicated test
# ---------------------------------------------------------------------------


@patch("apps.api.routers.screen.screen_calls", return_value=MOCK_CALL_RESULTS)
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_poll_completed_call_run(mock_clients, mock_screen, client):
    """Poll a completed call screen returns results with cost_basis field."""
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())
    resp = client.post("/api/screen/calls", json={
        **ALPACA_KEYS,
        "symbol": "AAPL",
        "cost_basis": 195.0,
    })
    run_id = resp.json()["run_id"]

    time.sleep(0.5)

    poll = client.get(f"/api/screen/runs/{run_id}")
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
def test_put_results_match_schema(mock_clients, mock_screen, client):
    """Completed put results contain every field from PutResultSchema."""
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())
    resp = client.post("/api/screen/puts", json={
        **ALPACA_KEYS,
        "symbols": ["AAPL"],
        "buying_power": 50000.0,
    })
    run_id = resp.json()["run_id"]

    time.sleep(0.5)

    poll = client.get(f"/api/screen/runs/{run_id}")
    data = poll.json()
    assert data["status"] == "completed"

    result = data["results"][0]
    expected_fields = set(PutResultSchema.model_fields.keys())
    assert set(result.keys()) == expected_fields

    # Verify specific values match our SAMPLE_PUT
    assert result["symbol"] == "AAPL250418P00200000"
    assert result["underlying"] == "AAPL"
    assert result["strike"] == 200.0
    assert result["dte"] == 30
    assert result["premium"] == 3.50
    assert result["delta"] == -0.25
    assert result["oi"] == 1500
    assert result["spread"] == 0.03
    assert result["annualized_return"] == 21.35
