"""Tests for positions and account endpoints.

Uses mocked Alpaca clients to avoid real API calls.
Shared fixtures from conftest.py.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.tests.conftest import ALPACA_QUERY_PARAMS
from alpaca.trading.enums import AssetClass


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


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
def test_positions_returns_wheel_state(mock_clients, client):
    """Positions endpoint returns positions list and wheel state."""
    trade_client = MagicMock()
    mock_positions = [
        _mock_position("AAPL", 100, 180.0, AssetClass.US_EQUITY),
    ]
    trade_client.get_all_positions.return_value = mock_positions
    mock_clients.return_value = (trade_client, MagicMock(), MagicMock())

    resp = client.get("/api/positions", params=ALPACA_QUERY_PARAMS)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["positions"]) == 1
    assert data["positions"][0]["symbol"] == "AAPL"
    assert "AAPL" in data["wheel_state"]
    assert data["wheel_state"]["AAPL"]["type"] == "long_shares"


@patch("apps.api.routers.positions.create_alpaca_clients")
def test_positions_empty(mock_clients, client):
    """Empty portfolio returns empty positions and wheel state."""
    trade_client = MagicMock()
    trade_client.get_all_positions.return_value = []
    mock_clients.return_value = (trade_client, MagicMock(), MagicMock())

    resp = client.get("/api/positions", params=ALPACA_QUERY_PARAMS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["positions"] == []
    assert data["wheel_state"] == {}


@patch("apps.api.routers.positions.create_alpaca_clients")
def test_positions_api_error_returns_502(mock_clients, client):
    """API failure returns 502."""
    trade_client = MagicMock()
    trade_client.get_all_positions.side_effect = Exception("Connection refused")
    mock_clients.return_value = (trade_client, MagicMock(), MagicMock())

    resp = client.get("/api/positions", params=ALPACA_QUERY_PARAMS)
    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# Account endpoint
# ---------------------------------------------------------------------------


@patch("apps.api.routers.positions.create_alpaca_clients")
def test_account_returns_summary(mock_clients, client):
    """Account endpoint returns buying power, portfolio value, cash, risk."""
    trade_client = MagicMock()

    account = MagicMock()
    account.buying_power = "100000.00"
    account.portfolio_value = "250000.00"
    account.cash = "100000.00"
    trade_client.get_account.return_value = account
    trade_client.get_all_positions.return_value = []
    mock_clients.return_value = (trade_client, MagicMock(), MagicMock())

    resp = client.get("/api/account", params=ALPACA_QUERY_PARAMS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["buying_power"] == "100000.00"
    assert data["portfolio_value"] == "250000.00"
    assert data["cash"] == "100000.00"
    assert data["capital_at_risk"] == 0


@patch("apps.api.routers.positions.create_alpaca_clients")
def test_account_with_positions_calculates_risk(mock_clients, client):
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

    resp = client.get("/api/account", params=ALPACA_QUERY_PARAMS)
    assert resp.status_code == 200
    data = resp.json()
    # Risk = avg_entry_price * qty = 180 * 100 = 18000
    assert data["capital_at_risk"] == 18000.0


@patch("apps.api.routers.positions.create_alpaca_clients")
def test_account_api_error_returns_502(mock_clients, client):
    """API failure returns 502."""
    trade_client = MagicMock()
    trade_client.get_account.side_effect = Exception("Auth failed")
    mock_clients.return_value = (trade_client, MagicMock(), MagicMock())

    resp = client.get("/api/account", params=ALPACA_QUERY_PARAMS)
    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# Missing required keys returns 422
# ---------------------------------------------------------------------------


def test_positions_missing_keys_returns_422(client):
    """Omitting required alpaca_api_key or alpaca_secret_key returns 422."""
    # Missing both keys
    resp = client.get("/api/positions")
    assert resp.status_code == 422

    # Missing secret key only
    resp = client.get("/api/positions", params={"alpaca_api_key": "test-key"})
    assert resp.status_code == 422

    # Missing api key only
    resp = client.get("/api/positions", params={"alpaca_secret_key": "test-secret"})
    assert resp.status_code == 422


def test_account_missing_keys_returns_422(client):
    """Omitting required keys on account endpoint returns 422."""
    resp = client.get("/api/account")
    assert resp.status_code == 422
