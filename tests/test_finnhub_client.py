"""Tests for screener.finnhub_client — rate limiting, retry, metric fallback chains."""

import logging as stdlib_logging
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

import pytest

import finnhub

# ---------------------------------------------------------------------------
# Helpers for mocking FinnhubAPIException
# ---------------------------------------------------------------------------

def _make_api_exception(status_code: int, message: str = "error") -> finnhub.FinnhubAPIException:
    """Create a FinnhubAPIException with a mocked response object."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = {"error": message}
    return finnhub.FinnhubAPIException(mock_response)


# ===========================================================================
# TestThrottle
# ===========================================================================

class TestThrottle:
    """Verify _throttle() enforces minimum interval between API calls."""

    @patch("screener.finnhub_client.time")
    def test_throttle_sleeps_when_calls_too_close(self, mock_time):
        """When elapsed < call_interval, _throttle sleeps the difference."""
        from screener.finnhub_client import FinnhubClient

        # First monotonic() call returns current time (for elapsed calculation)
        # elapsed = 100.3 - 100.0 = 0.3s, which is < 1.1s default interval
        # So it should sleep 1.1 - 0.3 = 0.8s
        # Second monotonic() call sets _last_call_time
        mock_time.monotonic.side_effect = [100.3, 100.3]
        mock_time.sleep = MagicMock()

        with patch("screener.finnhub_client.finnhub"):
            with patch("screener.finnhub_client.require_finnhub_key", return_value="fake"):
                client = FinnhubClient(api_key="fake")
                client._last_call_time = 100.0
                client._throttle()

        mock_time.sleep.assert_called_once_with(pytest.approx(0.8, abs=0.01))

    @patch("screener.finnhub_client.time")
    def test_throttle_no_sleep_when_calls_far_apart(self, mock_time):
        """When elapsed >= call_interval, _throttle does not sleep."""
        from screener.finnhub_client import FinnhubClient

        # elapsed = 105.0 - 100.0 = 5.0s, which is >= 1.1s
        mock_time.monotonic.side_effect = [105.0, 105.0]
        mock_time.sleep = MagicMock()

        with patch("screener.finnhub_client.finnhub"):
            with patch("screener.finnhub_client.require_finnhub_key", return_value="fake"):
                client = FinnhubClient(api_key="fake")
                client._last_call_time = 100.0
                client._throttle()

        mock_time.sleep.assert_not_called()


# ===========================================================================
# TestRetry429
# ===========================================================================

class TestRetry429:
    """Verify 429 retry logic: one retry after 5s, second 429 propagates."""

    @patch("screener.finnhub_client.time")
    def test_429_retries_once_after_5s(self, mock_time):
        """First 429 triggers a 5s sleep and retry; retry succeeds."""
        from screener.finnhub_client import FinnhubClient

        mock_time.monotonic.return_value = 1000.0
        mock_time.sleep = MagicMock()

        exc_429 = _make_api_exception(429, "Rate limit exceeded")
        mock_func = MagicMock(side_effect=[exc_429, {"result": "ok"}])

        with patch("screener.finnhub_client.finnhub") as mock_finnhub:
            mock_finnhub.FinnhubAPIException = finnhub.FinnhubAPIException
            with patch("screener.finnhub_client.require_finnhub_key", return_value="fake"):
                client = FinnhubClient(api_key="fake")
                client._last_call_time = 0.0
                result = client._call_with_retry(mock_func, "arg1", symbol="AAPL", endpoint="test")

        assert result == {"result": "ok"}
        assert mock_func.call_count == 2
        # Should have slept 5s for retry (plus throttle sleeps)
        sleep_calls = [c[0][0] for c in mock_time.sleep.call_args_list]
        assert 5 in sleep_calls

    @patch("screener.finnhub_client.time")
    def test_double_429_propagates(self, mock_time):
        """When retry also returns 429, the exception propagates."""
        from screener.finnhub_client import FinnhubClient

        mock_time.monotonic.return_value = 1000.0
        mock_time.sleep = MagicMock()

        exc_429_1 = _make_api_exception(429, "Rate limit exceeded")
        exc_429_2 = _make_api_exception(429, "Rate limit exceeded again")
        mock_func = MagicMock(side_effect=[exc_429_1, exc_429_2])

        with patch("screener.finnhub_client.finnhub") as mock_finnhub:
            mock_finnhub.FinnhubAPIException = finnhub.FinnhubAPIException
            with patch("screener.finnhub_client.require_finnhub_key", return_value="fake"):
                client = FinnhubClient(api_key="fake")
                client._last_call_time = 0.0

                with pytest.raises(finnhub.FinnhubAPIException):
                    client._call_with_retry(mock_func, "arg1", symbol="AAPL", endpoint="test")

        assert mock_func.call_count == 2


# ===========================================================================
# TestNon429Exception
# ===========================================================================

class TestNon429Exception:
    """Verify non-429 exceptions re-raise immediately without retry."""

    @patch("screener.finnhub_client.time")
    def test_403_reraises_immediately(self, mock_time):
        """A 403 FinnhubAPIException re-raises without retry."""
        from screener.finnhub_client import FinnhubClient

        mock_time.monotonic.return_value = 1000.0
        mock_time.sleep = MagicMock()

        exc_403 = _make_api_exception(403, "Forbidden")
        mock_func = MagicMock(side_effect=exc_403)

        with patch("screener.finnhub_client.finnhub") as mock_finnhub:
            mock_finnhub.FinnhubAPIException = finnhub.FinnhubAPIException
            with patch("screener.finnhub_client.require_finnhub_key", return_value="fake"):
                client = FinnhubClient(api_key="fake")
                client._last_call_time = 0.0

                with pytest.raises(finnhub.FinnhubAPIException) as exc_info:
                    client._call_with_retry(mock_func, "arg1", symbol="AAPL", endpoint="test")

        assert exc_info.value.status_code == 403
        assert mock_func.call_count == 1


# ===========================================================================
# TestCompanyProfile
# ===========================================================================

class TestCompanyProfile:
    """Verify company_profile delegates to SDK and returns data."""

    @patch("screener.finnhub_client.time")
    def test_company_profile_returns_data(self, mock_time):
        """company_profile calls company_profile2 and returns the dict."""
        from screener.finnhub_client import FinnhubClient

        mock_time.monotonic.return_value = 1000.0
        mock_time.sleep = MagicMock()

        sample_profile = {
            "ticker": "AAPL",
            "marketCapitalization": 2800000,
            "finnhubIndustry": "Technology",
        }

        with patch("screener.finnhub_client.finnhub") as mock_finnhub:
            mock_sdk_client = MagicMock()
            mock_sdk_client.company_profile2.return_value = sample_profile
            mock_finnhub.Client.return_value = mock_sdk_client
            mock_finnhub.FinnhubAPIException = finnhub.FinnhubAPIException

            with patch("screener.finnhub_client.require_finnhub_key", return_value="fake"):
                client = FinnhubClient(api_key="fake")
                result = client.company_profile(symbol="AAPL")

        assert result == sample_profile
        mock_sdk_client.company_profile2.assert_called_once_with(symbol="AAPL")

    @patch("screener.finnhub_client.time")
    def test_company_profile_empty_response(self, mock_time):
        """Empty profile response (symbol not found) returns empty dict."""
        from screener.finnhub_client import FinnhubClient

        mock_time.monotonic.return_value = 1000.0
        mock_time.sleep = MagicMock()

        with patch("screener.finnhub_client.finnhub") as mock_finnhub:
            mock_sdk_client = MagicMock()
            mock_sdk_client.company_profile2.return_value = {}
            mock_finnhub.Client.return_value = mock_sdk_client
            mock_finnhub.FinnhubAPIException = finnhub.FinnhubAPIException

            with patch("screener.finnhub_client.require_finnhub_key", return_value="fake"):
                client = FinnhubClient(api_key="fake")
                result = client.company_profile(symbol="INVALID")

        assert result == {}


# ===========================================================================
# TestCompanyMetrics
# ===========================================================================

class TestCompanyMetrics:
    """Verify company_metrics delegates to SDK and returns data."""

    @patch("screener.finnhub_client.time")
    def test_company_metrics_returns_data(self, mock_time):
        """company_metrics calls company_basic_financials and returns dict."""
        from screener.finnhub_client import FinnhubClient

        mock_time.monotonic.return_value = 1000.0
        mock_time.sleep = MagicMock()

        sample_metrics = {
            "metric": {
                "totalDebtToEquity": 1.5,
                "netProfitMarginTTM": 25.3,
                "revenueGrowthQuarterlyYoy": 8.2,
            },
            "metricType": "all",
            "symbol": "AAPL",
        }

        with patch("screener.finnhub_client.finnhub") as mock_finnhub:
            mock_sdk_client = MagicMock()
            mock_sdk_client.company_basic_financials.return_value = sample_metrics
            mock_finnhub.Client.return_value = mock_sdk_client
            mock_finnhub.FinnhubAPIException = finnhub.FinnhubAPIException

            with patch("screener.finnhub_client.require_finnhub_key", return_value="fake"):
                client = FinnhubClient(api_key="fake")
                result = client.company_metrics(symbol="AAPL")

        assert result == sample_metrics
        mock_sdk_client.company_basic_financials.assert_called_once_with("AAPL", "all")


# ===========================================================================
# TestExtractMetric
# ===========================================================================

class TestExtractMetric:
    """Verify extract_metric resolves values through fallback chains."""

    def test_primary_key_present(self):
        """Returns primary key value when it exists."""
        from screener.finnhub_client import extract_metric

        metrics = {"totalDebtToEquity": 1.5, "totalDebtToEquityQuarterly": 2.0}
        result = extract_metric(metrics, "debt_equity")
        assert result == 1.5

    def test_fallback_key_used(self):
        """Returns fallback key value when primary is missing."""
        from screener.finnhub_client import extract_metric

        metrics = {"totalDebtToEquityQuarterly": 2.0}
        result = extract_metric(metrics, "debt_equity")
        assert result == 2.0

    def test_all_keys_missing_returns_none(self):
        """Returns None when all keys in chain are missing."""
        from screener.finnhub_client import extract_metric

        metrics = {"unrelatedKey": 42}
        result = extract_metric(metrics, "debt_equity")
        assert result is None

    def test_none_value_skipped(self):
        """Skips keys whose value is None and tries the next."""
        from screener.finnhub_client import extract_metric

        metrics = {"totalDebtToEquity": None, "totalDebtToEquityQuarterly": 3.0}
        result = extract_metric(metrics, "debt_equity")
        assert result == 3.0

    def test_returns_float(self):
        """Returned value is always a float (not int)."""
        from screener.finnhub_client import extract_metric

        metrics = {"netProfitMarginTTM": 25}
        result = extract_metric(metrics, "net_margin")
        assert result == 25.0
        assert isinstance(result, float)

    def test_unknown_chain_returns_none(self):
        """Unknown chain name returns None (empty chain)."""
        from screener.finnhub_client import extract_metric

        metrics = {"someKey": 1.0}
        result = extract_metric(metrics, "nonexistent_chain")
        assert result is None


# ===========================================================================
# TestFallbackChains
# ===========================================================================

class TestFallbackChains:
    """Verify METRIC_FALLBACK_CHAINS has all required entries."""

    def test_debt_equity_chain_exists(self):
        from screener.finnhub_client import METRIC_FALLBACK_CHAINS
        assert "debt_equity" in METRIC_FALLBACK_CHAINS
        assert len(METRIC_FALLBACK_CHAINS["debt_equity"]) >= 2

    def test_net_margin_chain_exists(self):
        from screener.finnhub_client import METRIC_FALLBACK_CHAINS
        assert "net_margin" in METRIC_FALLBACK_CHAINS
        assert len(METRIC_FALLBACK_CHAINS["net_margin"]) >= 2

    def test_sales_growth_chain_exists(self):
        from screener.finnhub_client import METRIC_FALLBACK_CHAINS
        assert "sales_growth" in METRIC_FALLBACK_CHAINS
        assert len(METRIC_FALLBACK_CHAINS["sales_growth"]) >= 2

    def test_debt_equity_chain_keys(self):
        from screener.finnhub_client import METRIC_FALLBACK_CHAINS
        chain = METRIC_FALLBACK_CHAINS["debt_equity"]
        assert chain == [
            "totalDebtToEquity",
            "totalDebtToEquityQuarterly",
            "totalDebtToEquityAnnual",
        ]

    def test_net_margin_chain_keys(self):
        from screener.finnhub_client import METRIC_FALLBACK_CHAINS
        chain = METRIC_FALLBACK_CHAINS["net_margin"]
        assert chain == [
            "netProfitMarginTTM",
            "netProfitMarginAnnual",
            "netMargin",
        ]

    def test_sales_growth_chain_keys(self):
        from screener.finnhub_client import METRIC_FALLBACK_CHAINS
        chain = METRIC_FALLBACK_CHAINS["sales_growth"]
        assert chain == [
            "revenueGrowthQuarterlyYoy",
            "revenueGrowth5Y",
            "revenueGrowth3Y",
        ]


# ===========================================================================
# TestDebugLogging
# ===========================================================================

class TestDebugLogging:
    """Verify API calls are logged at DEBUG level."""

    @patch("screener.finnhub_client.time")
    def test_successful_call_logs_debug(self, mock_time):
        """Successful API call produces a DEBUG log with symbol and endpoint."""
        from screener.finnhub_client import FinnhubClient

        mock_time.monotonic.side_effect = [1000.0, 1000.0, 1000.0, 1000.5]
        mock_time.sleep = MagicMock()

        with patch("screener.finnhub_client.finnhub") as mock_finnhub:
            mock_sdk_client = MagicMock()
            mock_sdk_client.company_profile2.return_value = {"ticker": "AAPL"}
            mock_finnhub.Client.return_value = mock_sdk_client
            mock_finnhub.FinnhubAPIException = finnhub.FinnhubAPIException

            with patch("screener.finnhub_client.require_finnhub_key", return_value="fake"):
                client = FinnhubClient(api_key="fake")

                with patch("screener.finnhub_client.logger") as mock_logger:
                    client.company_profile(symbol="AAPL")
                    mock_logger.debug.assert_called_once()
                    log_msg = mock_logger.debug.call_args[0][0] % mock_logger.debug.call_args[0][1:]
                    assert "AAPL" in log_msg
                    assert "profile2" in log_msg
