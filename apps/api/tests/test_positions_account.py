"""Tests for positions and account endpoints.

Uses mock auth + mock key retrieval instead of raw Alpaca query params.
Shared fixtures from conftest.py.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from apps.api.main import app
from alpaca.trading.enums import AssetClass


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_key_retrieval():
    """Mock retrieve_alpaca_keys in the positions router to return test credentials."""
    with patch(
        "apps.api.routers.positions.retrieve_alpaca_keys",
        return_value=("test-key", "test-secret", True),
    ) as m:
        yield m


def _mock_position(symbol, qty, avg_price, asset_class, market_value="10000"):
    """Build a mock position object matching Alpaca SDK shape."""
    pos = MagicMock()
    pos.symbol = symbol
    pos.qty = str(qty)
    pos.avg_entry_price = str(avg_price)
    pos.market_value = market_value
    pos.asset_class = asset_class
    pos.side = "long"
    return pos


# ---------------------------------------------------------------------------
# Positions endpoint
# ---------------------------------------------------------------------------


@patch("apps.api.routers.positions.create_alpaca_clients")
def test_positions_returns_wheel_state(
    mock_clients, client, mock_auth, mock_db, mock_key_retrieval, auth_headers,
):
    """Positions endpoint returns positions list and wheel state."""
    trade_client = MagicMock()
    mock_positions = [
        _mock_position("AAPL", 100, 180.0, AssetClass.US_EQUITY),
    ]
    trade_client.get_all_positions.return_value = mock_positions
    mock_clients.return_value = (trade_client, MagicMock(), MagicMock())

    resp = client.get("/api/positions", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["positions"]) == 1
    assert data["positions"][0]["symbol"] == "AAPL"
    assert "AAPL" in data["wheel_state"]
    assert data["wheel_state"]["AAPL"]["type"] == "long_shares"


@patch("apps.api.routers.positions.create_alpaca_clients")
def test_positions_empty(
    mock_clients, client, mock_auth, mock_db, mock_key_retrieval, auth_headers,
):
    """Empty portfolio returns empty positions and wheel state."""
    trade_client = MagicMock()
    trade_client.get_all_positions.return_value = []
    mock_clients.return_value = (trade_client, MagicMock(), MagicMock())

    resp = client.get("/api/positions", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["positions"] == []
    assert data["wheel_state"] == {}


@patch("apps.api.routers.positions.create_alpaca_clients")
def test_positions_api_error_returns_502(
    mock_clients, client, mock_auth, mock_db, mock_key_retrieval, auth_headers,
):
    """API failure returns 502."""
    trade_client = MagicMock()
    trade_client.get_all_positions.side_effect = Exception("Connection refused")
    mock_clients.return_value = (trade_client, MagicMock(), MagicMock())

    resp = client.get("/api/positions", headers=auth_headers)
    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# Account endpoint
# ---------------------------------------------------------------------------


@patch("apps.api.routers.positions.create_alpaca_clients")
def test_account_returns_summary(
    mock_clients, client, mock_auth, mock_db, mock_key_retrieval, auth_headers,
):
    """Account endpoint returns buying power, portfolio value, cash, risk."""
    trade_client = MagicMock()

    account = MagicMock()
    account.buying_power = "100000.00"
    account.portfolio_value = "250000.00"
    account.cash = "100000.00"
    trade_client.get_account.return_value = account
    trade_client.get_all_positions.return_value = []
    mock_clients.return_value = (trade_client, MagicMock(), MagicMock())

    resp = client.get("/api/account", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["buying_power"] == "100000.00"
    assert data["portfolio_value"] == "250000.00"
    assert data["cash"] == "100000.00"
    assert data["capital_at_risk"] == 0


@patch("apps.api.routers.positions.create_alpaca_clients")
def test_account_with_positions_calculates_risk(
    mock_clients, client, mock_auth, mock_db, mock_key_retrieval, auth_headers,
):
    """Account risk includes equity positions."""
    trade_client = MagicMock()

    account = MagicMock()
    account.buying_power = "80000.00"
    account.portfolio_value = "200000.00"
    account.cash = "80000.00"
    trade_client.get_account.return_value = account

    pos = _mock_position("AAPL", 100, 180.0, AssetClass.US_EQUITY)
    trade_client.get_all_positions.return_value = [pos]
    mock_clients.return_value = (trade_client, MagicMock(), MagicMock())

    resp = client.get("/api/account", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["capital_at_risk"] == 18000.0


@patch("apps.api.routers.positions.create_alpaca_clients")
def test_account_api_error_returns_502(
    mock_clients, client, mock_auth, mock_db, mock_key_retrieval, auth_headers,
):
    """API failure returns 502."""
    trade_client = MagicMock()
    trade_client.get_account.side_effect = Exception("Auth failed")
    mock_clients.return_value = (trade_client, MagicMock(), MagicMock())

    resp = client.get("/api/account", headers=auth_headers)
    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# Auth error paths
# ---------------------------------------------------------------------------


def test_positions_missing_auth_returns_401(client):
    """Request without Authorization header returns 401."""
    resp = client.get("/api/positions")
    assert resp.status_code == 401


def test_account_missing_auth_returns_401(client):
    """Request without Authorization header returns 401."""
    resp = client.get("/api/account")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Missing stored keys returns 400
# ---------------------------------------------------------------------------


@patch("apps.api.routers.positions.retrieve_alpaca_keys")
def test_positions_missing_keys_returns_400(
    mock_retrieve, client, mock_auth, mock_db, auth_headers,
):
    """When no keys are stored in DB, returns 400 with descriptive message."""
    mock_retrieve.side_effect = HTTPException(
        status_code=400,
        detail="Alpaca API keys not configured. Add keys in Settings.",
    )
    resp = client.get("/api/positions", headers=auth_headers)
    assert resp.status_code == 400
    assert "not configured" in resp.json()["detail"]


@patch("apps.api.routers.positions.retrieve_alpaca_keys")
def test_account_missing_keys_returns_400(
    mock_retrieve, client, mock_auth, mock_db, auth_headers,
):
    """When no keys are stored in DB, returns 400 with descriptive message."""
    mock_retrieve.side_effect = HTTPException(
        status_code=400,
        detail="Alpaca API keys not configured. Add keys in Settings.",
    )
    resp = client.get("/api/account", headers=auth_headers)
    assert resp.status_code == 400
    assert "not configured" in resp.json()["detail"]
