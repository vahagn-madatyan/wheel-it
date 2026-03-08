"""Tests for Finnhub API key loading in config/credentials.py."""

import importlib
import os

import pytest


def test_finnhub_key_loaded(monkeypatch):
    """When FINNHUB_API_KEY is set in environment, the module-level variable holds the value."""
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key-abc123")
    import config.credentials as creds

    importlib.reload(creds)
    assert creds.FINNHUB_API_KEY == "test-key-abc123"


def test_finnhub_key_missing_is_none(monkeypatch):
    """When FINNHUB_API_KEY is not in environment, the module-level variable is None."""
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    import config.credentials as creds

    importlib.reload(creds)
    assert creds.FINNHUB_API_KEY is None


def test_require_finnhub_key_returns_key(monkeypatch):
    """When key is set, require_finnhub_key() returns it."""
    import config.credentials as creds

    monkeypatch.setattr(creds, "FINNHUB_API_KEY", "test-key-xyz789")
    assert creds.require_finnhub_key() == "test-key-xyz789"


def test_require_finnhub_key_raises_when_missing(monkeypatch):
    """When key is not set, require_finnhub_key() raises EnvironmentError with actionable message."""
    import config.credentials as creds

    monkeypatch.setattr(creds, "FINNHUB_API_KEY", None)
    with pytest.raises(EnvironmentError) as exc_info:
        creds.require_finnhub_key()

    error_msg = str(exc_info.value)
    assert "FINNHUB_API_KEY" in error_msg
    assert ".env" in error_msg
    assert "finnhub.io/register" in error_msg
