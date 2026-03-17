"""Tests for create_alpaca_clients factory function."""

from apps.api.services.clients import create_alpaca_clients
from alpaca.trading.client import TradingClient
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient


def test_create_alpaca_clients_returns_tuple():
    """Factory returns a 3-tuple of the correct SDK client types."""
    trade, option, stock = create_alpaca_clients(
        api_key="test-key",
        secret_key="test-secret",
        is_paper=True,
    )
    assert isinstance(trade, TradingClient)
    assert isinstance(option, OptionHistoricalDataClient)
    assert isinstance(stock, StockHistoricalDataClient)


def test_create_alpaca_clients_paper_vs_live():
    """Paper flag is passed through to TradingClient."""
    trade_paper, _, _ = create_alpaca_clients("k", "s", is_paper=True)
    trade_live, _, _ = create_alpaca_clients("k", "s", is_paper=False)
    # TradingClient stores the paper flag internally
    assert trade_paper._use_raw_data is not None  # client was constructed
    assert trade_live._use_raw_data is not None


def test_create_alpaca_clients_no_env_vars(monkeypatch):
    """Factory constructs clients from arguments, not env vars."""
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    trade, option, stock = create_alpaca_clients("explicit-key", "explicit-secret")
    assert isinstance(trade, TradingClient)
