"""Finnhub API client with rate limiting, retry on 429, and metric fallback chains.

Wraps the finnhub-python SDK to provide throttled access to company profile
and basic financials endpoints. Designed for screening 200+ symbols without
tripping the free-tier 60 calls/min rate limit.
"""

import logging as stdlib_logging
import time

import finnhub
from config.credentials import require_finnhub_key

logger = stdlib_logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Metric fallback chains (SAFE-04)
# ---------------------------------------------------------------------------
# Finnhub metric key names are not fully documented. These chains try the
# primary key first, then alternate suffixes. Returns first non-None value.

METRIC_FALLBACK_CHAINS: dict[str, list[str]] = {
    "debt_equity": [
        "totalDebtToEquity",
        "totalDebtToEquityQuarterly",
        "totalDebtToEquityAnnual",
    ],
    "net_margin": [
        "netProfitMarginTTM",
        "netProfitMarginAnnual",
        "netMargin",
    ],
    "sales_growth": [
        "revenueGrowthQuarterlyYoy",
        "revenueGrowth5Y",
        "revenueGrowth3Y",
    ],
}


def extract_metric(metrics: dict, chain_name: str) -> float | None:
    """Extract a metric value using fallback key chain.

    Args:
        metrics: The 'metric' dict from Finnhub basic_financials response.
        chain_name: Key into METRIC_FALLBACK_CHAINS.

    Returns:
        First non-None value from the chain as a float, or None if all
        keys are missing or null.
    """
    chain = METRIC_FALLBACK_CHAINS.get(chain_name, [])
    for key in chain:
        value = metrics.get(key)
        if value is not None:
            return float(value)
    return None


class FinnhubClient:
    """Rate-limited Finnhub API client with 429 retry logic.

    Args:
        api_key: Finnhub API key. If None, reads from FINNHUB_API_KEY env var.
        call_interval: Minimum seconds between API calls. Default 1.1s
            (~54 calls/min, safely under the 60/min free-tier limit).
    """

    def __init__(self, api_key: str | None = None, call_interval: float = 1.1):
        self._key = api_key or require_finnhub_key()
        self._client = finnhub.Client(api_key=self._key)
        self._call_interval = call_interval
        self._last_call_time: float = 0.0

    def _throttle(self) -> None:
        """Sleep to maintain at least call_interval seconds between calls."""
        elapsed = time.monotonic() - self._last_call_time
        if elapsed < self._call_interval:
            time.sleep(self._call_interval - elapsed)
        self._last_call_time = time.monotonic()

    def _call_with_retry(self, func, *args, symbol: str = "", endpoint: str = ""):
        """Call a Finnhub API function with throttle, logging, and 429 retry.

        On first 429 FinnhubAPIException: logs WARNING, sleeps 5s, retries once.
        On second 429: lets the exception propagate (caller handles skip).
        Non-429 FinnhubAPIException: re-raises immediately.

        Args:
            func: Callable (SDK method) to invoke.
            *args: Positional arguments for func.
            symbol: Symbol being fetched (for logging).
            endpoint: Endpoint name (for logging).

        Returns:
            The API response (dict).
        """
        self._throttle()
        start = time.monotonic()
        try:
            result = func(*args)
            duration = time.monotonic() - start
            logger.debug("%s %s completed in %.2fs", symbol, endpoint, duration)
            return result
        except finnhub.FinnhubAPIException as e:
            if e.status_code == 429:
                logger.warning("%s %s got 429, retrying after 5s", symbol, endpoint)
                time.sleep(5)
                self._throttle()
                # Second attempt -- let exception propagate if it also fails
                result = func(*args)
                duration = time.monotonic() - start
                logger.debug(
                    "%s %s completed in %.2fs (after retry)",
                    symbol,
                    endpoint,
                    duration,
                )
                return result
            raise

    def company_profile(self, symbol: str) -> dict:
        """Fetch company profile via Finnhub company_profile2 endpoint.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL").

        Returns:
            Dict with keys like marketCapitalization, finnhubIndustry, ticker.
            Returns empty dict if symbol not found.
        """
        return self._call_with_retry(
            lambda: self._client.company_profile2(symbol=symbol),
            symbol=symbol,
            endpoint="profile2",
        )

    def company_metrics(self, symbol: str) -> dict:
        """Fetch basic financials via Finnhub company_basic_financials endpoint.

        Args:
            symbol: Stock ticker symbol (e.g., "AAPL").

        Returns:
            Dict with 'metric' key containing financial ratios.
            Returns dict with empty metric sub-dict if data unavailable.
        """
        return self._call_with_retry(
            lambda: self._client.company_basic_financials(symbol, "all"),
            symbol=symbol,
            endpoint="basic_financials",
        )
