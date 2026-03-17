"""Shared test fixtures for the API test suite.

Provides:
- app_client: httpx.AsyncClient wired to the FastAPI app via ASGITransport
- Synchronous client fixture for simpler tests
- Sample PutRecommendation / CallRecommendation instances
- Mock fixtures for Alpaca SDK client constructors and screener functions
- Auth + DB mock fixtures for S02 key management tests
"""

import base64
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import pytest_asyncio
from jose import jwt

from apps.api.main import app
from apps.api.services.auth import get_current_user
from apps.api.services.database import get_db
from screener.call_screener import CallRecommendation
from screener.put_screener import PutRecommendation


# ---------------------------------------------------------------------------
# S02 auth constants
# ---------------------------------------------------------------------------

TEST_JWT_SECRET = "test-supabase-jwt-secret-for-unit-tests"
TEST_USER_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
TEST_ENCRYPTION_KEY = base64.b64encode(os.urandom(32)).decode()


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


# ---------------------------------------------------------------------------
# S02: Auth + DB mock fixtures for key management tests
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_auth():
    """Override get_current_user to return TEST_USER_ID without JWT validation."""
    app.dependency_overrides[get_current_user] = lambda: TEST_USER_ID
    yield TEST_USER_ID
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return Authorization headers with a valid test JWT."""
    payload = {
        "sub": TEST_USER_ID,
        "aud": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_db():
    """Override get_db dependency with an AsyncMock mimicking asyncpg.Connection."""
    mock_conn = AsyncMock()
    # Default: fetch returns empty list, execute returns status string
    mock_conn.fetch.return_value = []
    mock_conn.execute.return_value = "INSERT 0 1"

    async def _override_get_db():
        yield mock_conn

    app.dependency_overrides[get_db] = _override_get_db
    yield mock_conn
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def mock_encryption(monkeypatch):
    """Set APP_ENCRYPTION_SECRET so encrypt_value/decrypt_value work in tests."""
    monkeypatch.setenv("APP_ENCRYPTION_SECRET", TEST_ENCRYPTION_KEY)

