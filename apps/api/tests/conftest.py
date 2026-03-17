"""Shared test fixtures for the API test suite.

Provides:
- app_client: httpx.AsyncClient wired to the FastAPI app via ASGITransport
- Synchronous client fixture for simpler tests
- Sample PutRecommendation / CallRecommendation instances
- Mock fixtures for Alpaca SDK client constructors and screener functions
"""

from unittest.mock import MagicMock

import httpx
import pytest
import pytest_asyncio

from apps.api.main import app
from screener.call_screener import CallRecommendation
from screener.put_screener import PutRecommendation


# ---------------------------------------------------------------------------
# Alpaca credential payloads
# ---------------------------------------------------------------------------

ALPACA_KEYS = {
    "alpaca_api_key": "test-key",
    "alpaca_secret_key": "test-secret",
    "is_paper": True,
}

ALPACA_QUERY_PARAMS = {
    "alpaca_api_key": "test-key",
    "alpaca_secret_key": "test-secret",
    "is_paper": "true",
}


# ---------------------------------------------------------------------------
# Sample recommendation dataclass instances
# ---------------------------------------------------------------------------

SAMPLE_PUT = PutRecommendation(
    symbol="AAPL250418P00200000",
    underlying="AAPL",
    strike=200.0,
    dte=30,
    premium=3.50,
    delta=-0.25,
    oi=1500,
    spread=0.03,
    annualized_return=21.35,
)

SAMPLE_CALL = CallRecommendation(
    symbol="AAPL250418C00210000",
    underlying="AAPL",
    strike=210.0,
    dte=28,
    premium=2.80,
    delta=0.30,
    oi=800,
    spread=0.04,
    annualized_return=18.92,
    cost_basis=195.0,
)


# ---------------------------------------------------------------------------
# Async HTTPX client fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def app_client():
    """Async httpx client bound to the FastAPI app via ASGITransport."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ---------------------------------------------------------------------------
# Mock Alpaca client triple
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_alpaca_triple():
    """Returns (trade_client, option_client, stock_client) as MagicMocks."""
    return MagicMock(), MagicMock(), MagicMock()
