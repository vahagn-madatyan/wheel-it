"""Shared CLI credential helpers for both run-strategy and run-screener entry points."""

import logging as stdlib_logging

from config.credentials import ALPACA_API_KEY, ALPACA_SECRET_KEY, IS_PAPER
from core.broker_client import BrokerClient

logger = stdlib_logging.getLogger(__name__)


def require_alpaca_credentials() -> tuple[str, str, bool]:
    """Return Alpaca credentials or raise SystemExit with actionable message.

    Returns:
        Tuple of (api_key, secret_key, is_paper).

    Raises:
        SystemExit: If ALPACA_API_KEY or ALPACA_SECRET_KEY is not set.
    """
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        raise SystemExit(
            "Error: --update-symbols requires Alpaca credentials for position protection.\n"
            "Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env"
        )
    return ALPACA_API_KEY, ALPACA_SECRET_KEY, IS_PAPER


def create_broker_client() -> BrokerClient:
    """Create BrokerClient with validated credentials."""
    key, secret, paper = require_alpaca_credentials()
    return BrokerClient(api_key=key, secret_key=secret, paper=paper)
