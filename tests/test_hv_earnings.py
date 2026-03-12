"""Tests for S08: HV Percentile and Earnings Calendar features.

Covers:
- compute_hv_percentile() math and edge cases
- filter_hv_percentile() pass/fail/None behavior
- filter_earnings_proximity() pass/fail/None behavior
- FinnhubClient.earnings_calendar() and earnings_for_symbol()
- Preset YAML files contain hv_percentile_min and earnings_exclusion_days
- ScreenedStock has hv_percentile, next_earnings_date, days_to_earnings fields
- Display table includes HV%ile column
- Config loader accepts EarningsConfig section
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
import yaml
from pathlib import Path

from models.screened_stock import FilterResult, ScreenedStock
from screener.config_loader import (
    EarningsConfig,
    ScreenerConfig,
    TechnicalsConfig,
    load_config,
    load_preset,
)
from screener.pipeline import (
    compute_hv_percentile,
    filter_earnings_proximity,
    filter_hv_percentile,
    run_stage_1_filters,
)


PRESETS_DIR = Path(__file__).resolve().parent.parent / "config" / "presets"


# ---------------------------------------------------------------------------
# compute_hv_percentile tests
# ---------------------------------------------------------------------------


class TestComputeHvPercentile:
    """Verify HV percentile computation from daily bars."""

    def _make_bars(self, n_days: int, base_price: float = 100.0, vol: float = 0.02) -> pd.DataFrame:
        """Generate synthetic daily close prices with controlled volatility."""
        np.random.seed(42)
        returns = np.random.normal(0, vol, n_days)
        prices = [base_price]
        for r in returns:
            prices.append(prices[-1] * np.exp(r))
        return pd.DataFrame({"close": prices})

    def test_returns_float_between_0_and_100(self):
        """HV percentile should be a float in [0, 100]."""
        bars = self._make_bars(300)
        result = compute_hv_percentile(bars)
        assert result is not None
        assert 0 <= result <= 100

    def test_returns_none_insufficient_data(self):
        """With fewer than lookback+1 bars, returns None."""
        bars = self._make_bars(200)  # Need 253 for default lookback=252
        result = compute_hv_percentile(bars)
        assert result is None

    def test_exact_threshold_data(self):
        """With exactly lookback+1 bars, should return a value."""
        bars = self._make_bars(252)  # 253 rows total (252+1 initial)
        result = compute_hv_percentile(bars)
        assert result is not None

    def test_high_vol_spike_gives_high_percentile(self):
        """A sudden vol spike at the end should produce high HV percentile."""
        np.random.seed(42)
        # 300 days of low vol, then 30 days of high vol
        low_vol_returns = np.random.normal(0, 0.005, 270)
        high_vol_returns = np.random.normal(0, 0.05, 30)
        returns = np.concatenate([low_vol_returns, high_vol_returns])
        prices = [100.0]
        for r in returns:
            prices.append(prices[-1] * np.exp(r))
        bars = pd.DataFrame({"close": prices})

        result = compute_hv_percentile(bars)
        assert result is not None
        assert result > 80  # Recent high vol → high percentile

    def test_low_vol_gives_low_percentile(self):
        """Consistently low vol at the end with high vol history → low percentile."""
        np.random.seed(42)
        # 270 days of high vol, then 30 days of low vol
        high_vol_returns = np.random.normal(0, 0.05, 270)
        low_vol_returns = np.random.normal(0, 0.005, 30)
        returns = np.concatenate([high_vol_returns, low_vol_returns])
        prices = [100.0]
        for r in returns:
            prices.append(prices[-1] * np.exp(r))
        bars = pd.DataFrame({"close": prices})

        result = compute_hv_percentile(bars)
        assert result is not None
        assert result < 20  # Recent low vol → low percentile

    def test_custom_window_and_lookback(self):
        """Custom hv_window and lookback params work correctly."""
        bars = self._make_bars(150)
        result = compute_hv_percentile(bars, hv_window=20, lookback=100)
        assert result is not None
        assert 0 <= result <= 100

    def test_result_is_rounded(self):
        """Result should be rounded to 1 decimal place."""
        bars = self._make_bars(300)
        result = compute_hv_percentile(bars)
        assert result is not None
        # Check it's rounded to 1 decimal
        assert result == round(result, 1)


# ---------------------------------------------------------------------------
# filter_hv_percentile tests
# ---------------------------------------------------------------------------


class TestFilterHvPercentile:
    """Verify HV percentile filter behavior."""

    def _config(self, hv_min: float = 30.0) -> ScreenerConfig:
        return ScreenerConfig(
            technicals=TechnicalsConfig(hv_percentile_min=hv_min),
        )

    def test_passes_above_threshold(self):
        stock = ScreenedStock.from_symbol("AAPL")
        stock.hv_percentile = 65.0
        result = filter_hv_percentile(stock, self._config(hv_min=30.0))
        assert result.passed is True
        assert result.filter_name == "hv_percentile"

    def test_fails_below_threshold(self):
        stock = ScreenedStock.from_symbol("AAPL")
        stock.hv_percentile = 15.0
        result = filter_hv_percentile(stock, self._config(hv_min=30.0))
        assert result.passed is False
        assert "15.0" in result.reason
        assert "30.0" in result.reason

    def test_passes_at_exact_threshold(self):
        stock = ScreenedStock.from_symbol("AAPL")
        stock.hv_percentile = 30.0
        result = filter_hv_percentile(stock, self._config(hv_min=30.0))
        assert result.passed is True

    def test_none_passes_with_neutral(self):
        """None hv_percentile should pass with neutral score (HVPR-01 + FIX-03)."""
        stock = ScreenedStock.from_symbol("AAPL")
        stock.hv_percentile = None
        result = filter_hv_percentile(stock, self._config(hv_min=30.0))
        assert result.passed is True
        assert "neutral" in result.reason.lower() or "no data" in result.reason.lower()

    def test_aggressive_threshold(self):
        """Aggressive preset uses lower threshold (20)."""
        stock = ScreenedStock.from_symbol("AAPL")
        stock.hv_percentile = 22.0
        result = filter_hv_percentile(stock, self._config(hv_min=20.0))
        assert result.passed is True

    def test_conservative_threshold_rejects(self):
        """Conservative preset uses higher threshold (50)."""
        stock = ScreenedStock.from_symbol("AAPL")
        stock.hv_percentile = 45.0
        result = filter_hv_percentile(stock, self._config(hv_min=50.0))
        assert result.passed is False


# ---------------------------------------------------------------------------
# filter_earnings_proximity tests
# ---------------------------------------------------------------------------


class TestFilterEarningsProximity:
    """Verify earnings proximity filter behavior."""

    def _config(self, exclusion_days: int = 14) -> ScreenerConfig:
        return ScreenerConfig(
            earnings=EarningsConfig(earnings_exclusion_days=exclusion_days),
        )

    def test_passes_when_no_earnings_data(self):
        """No earnings data → pass with neutral score."""
        stock = ScreenedStock.from_symbol("AAPL")
        stock.days_to_earnings = None
        result = filter_earnings_proximity(stock, self._config())
        assert result.passed is True
        assert result.filter_name == "earnings_proximity"

    def test_fails_when_earnings_within_window(self):
        """Earnings in 5 days with 14-day window → fail."""
        stock = ScreenedStock.from_symbol("AAPL")
        stock.days_to_earnings = 5
        result = filter_earnings_proximity(stock, self._config(exclusion_days=14))
        assert result.passed is False
        assert "5 days" in result.reason
        assert "14-day" in result.reason

    def test_passes_when_earnings_outside_window(self):
        """Earnings in 30 days with 14-day window → pass."""
        stock = ScreenedStock.from_symbol("AAPL")
        stock.days_to_earnings = 30
        result = filter_earnings_proximity(stock, self._config(exclusion_days=14))
        assert result.passed is True

    def test_fails_at_exact_boundary(self):
        """Earnings in exactly 14 days with 14-day window → fail (boundary inclusive)."""
        stock = ScreenedStock.from_symbol("AAPL")
        stock.days_to_earnings = 14
        result = filter_earnings_proximity(stock, self._config(exclusion_days=14))
        assert result.passed is False

    def test_passes_one_day_past_boundary(self):
        """Earnings in 15 days with 14-day window → pass."""
        stock = ScreenedStock.from_symbol("AAPL")
        stock.days_to_earnings = 15
        result = filter_earnings_proximity(stock, self._config(exclusion_days=14))
        assert result.passed is True

    def test_earnings_today_fails(self):
        """Earnings today (0 days) → fail."""
        stock = ScreenedStock.from_symbol("AAPL")
        stock.days_to_earnings = 0
        result = filter_earnings_proximity(stock, self._config(exclusion_days=7))
        assert result.passed is False

    def test_conservative_21_day_window(self):
        """Conservative preset uses 21-day window."""
        stock = ScreenedStock.from_symbol("AAPL")
        stock.days_to_earnings = 18
        result = filter_earnings_proximity(stock, self._config(exclusion_days=21))
        assert result.passed is False

    def test_aggressive_7_day_window(self):
        """Aggressive preset uses 7-day window — 10 days out passes."""
        stock = ScreenedStock.from_symbol("AAPL")
        stock.days_to_earnings = 10
        result = filter_earnings_proximity(stock, self._config(exclusion_days=7))
        assert result.passed is True


# ---------------------------------------------------------------------------
# FinnhubClient earnings tests
# ---------------------------------------------------------------------------


class TestFinnhubEarnings:
    """Verify FinnhubClient earnings calendar methods."""

    def test_earnings_calendar_returns_list(self):
        """earnings_calendar should return a list of dicts."""
        from screener.finnhub_client import FinnhubClient

        mock_sdk = MagicMock()
        mock_sdk.earnings_calendar.return_value = {
            "earningsCalendar": [
                {"date": "2026-03-20", "symbol": "AAPL", "hour": "amc"},
                {"date": "2026-03-25", "symbol": "MSFT", "hour": "bmo"},
            ]
        }

        client = FinnhubClient.__new__(FinnhubClient)
        client._client = mock_sdk
        client._call_interval = 0
        client._last_call_time = 0

        result = client.earnings_calendar()
        assert len(result) == 2
        assert result[0]["symbol"] == "AAPL"

    def test_earnings_calendar_empty_on_failure(self):
        """On API failure, earnings_calendar returns empty list."""
        from screener.finnhub_client import FinnhubClient

        mock_sdk = MagicMock()
        mock_sdk.earnings_calendar.side_effect = Exception("API error")

        client = FinnhubClient.__new__(FinnhubClient)
        client._client = mock_sdk
        client._call_interval = 0
        client._last_call_time = 0

        result = client.earnings_calendar()
        assert result == []

    def test_earnings_for_symbol_returns_date(self):
        """earnings_for_symbol returns the nearest earnings date."""
        from screener.finnhub_client import FinnhubClient

        tomorrow = (date.today() + timedelta(days=10)).isoformat()
        mock_sdk = MagicMock()
        mock_sdk.earnings_calendar.return_value = {
            "earningsCalendar": [
                {"date": tomorrow, "symbol": "AAPL"},
            ]
        }

        client = FinnhubClient.__new__(FinnhubClient)
        client._client = mock_sdk
        client._call_interval = 0
        client._last_call_time = 0

        result = client.earnings_for_symbol("AAPL")
        assert result is not None
        assert isinstance(result, date)
        assert result == date.fromisoformat(tomorrow)

    def test_earnings_for_symbol_none_when_no_data(self):
        """Returns None when no earnings data found."""
        from screener.finnhub_client import FinnhubClient

        mock_sdk = MagicMock()
        mock_sdk.earnings_calendar.return_value = {"earningsCalendar": []}

        client = FinnhubClient.__new__(FinnhubClient)
        client._client = mock_sdk
        client._call_interval = 0
        client._last_call_time = 0

        result = client.earnings_for_symbol("AAPL")
        assert result is None

    def test_earnings_for_symbol_none_on_error(self):
        """Returns None on API error instead of raising."""
        from screener.finnhub_client import FinnhubClient

        mock_sdk = MagicMock()
        mock_sdk.earnings_calendar.side_effect = Exception("API error")

        client = FinnhubClient.__new__(FinnhubClient)
        client._client = mock_sdk
        client._call_interval = 0
        client._last_call_time = 0

        result = client.earnings_for_symbol("AAPL")
        assert result is None


# ---------------------------------------------------------------------------
# Preset YAML tests for S08 fields
# ---------------------------------------------------------------------------


class TestPresetsS08:
    """Verify preset YAML files contain S08-specific thresholds."""

    def _load_preset(self, name: str) -> dict:
        with open(PRESETS_DIR / f"{name}.yaml") as f:
            return yaml.safe_load(f)

    def test_conservative_hv_percentile_min(self):
        data = self._load_preset("conservative")
        assert data["technicals"]["hv_percentile_min"] == 50

    def test_moderate_hv_percentile_min(self):
        data = self._load_preset("moderate")
        assert data["technicals"]["hv_percentile_min"] == 30

    def test_aggressive_hv_percentile_min(self):
        data = self._load_preset("aggressive")
        assert data["technicals"]["hv_percentile_min"] == 20

    def test_conservative_earnings_exclusion_days(self):
        data = self._load_preset("conservative")
        assert data["earnings"]["earnings_exclusion_days"] == 21

    def test_moderate_earnings_exclusion_days(self):
        data = self._load_preset("moderate")
        assert data["earnings"]["earnings_exclusion_days"] == 14

    def test_aggressive_earnings_exclusion_days(self):
        data = self._load_preset("aggressive")
        assert data["earnings"]["earnings_exclusion_days"] == 7

    def test_hv_percentile_min_differentiated(self):
        """All three presets use different hv_percentile_min thresholds."""
        values = set()
        for name in ("conservative", "moderate", "aggressive"):
            data = self._load_preset(name)
            values.add(data["technicals"]["hv_percentile_min"])
        assert len(values) == 3, "hv_percentile_min should differ across presets"

    def test_earnings_exclusion_days_differentiated(self):
        """All three presets use different earnings_exclusion_days thresholds."""
        values = set()
        for name in ("conservative", "moderate", "aggressive"):
            data = self._load_preset(name)
            values.add(data["earnings"]["earnings_exclusion_days"])
        assert len(values) == 3, "earnings_exclusion_days should differ across presets"


# ---------------------------------------------------------------------------
# ScreenedStock model S08 fields
# ---------------------------------------------------------------------------


class TestScreenedStockS08Fields:
    """Verify ScreenedStock has new S08 fields."""

    def test_hv_percentile_field_defaults_none(self):
        stock = ScreenedStock.from_symbol("AAPL")
        assert stock.hv_percentile is None

    def test_hv_percentile_field_settable(self):
        stock = ScreenedStock.from_symbol("AAPL")
        stock.hv_percentile = 75.5
        assert stock.hv_percentile == 75.5

    def test_next_earnings_date_defaults_none(self):
        stock = ScreenedStock.from_symbol("AAPL")
        assert stock.next_earnings_date is None

    def test_days_to_earnings_defaults_none(self):
        stock = ScreenedStock.from_symbol("AAPL")
        assert stock.days_to_earnings is None

    def test_days_to_earnings_settable(self):
        stock = ScreenedStock.from_symbol("AAPL")
        stock.days_to_earnings = 12
        assert stock.days_to_earnings == 12


# ---------------------------------------------------------------------------
# Config loader S08 integration
# ---------------------------------------------------------------------------


class TestConfigLoaderS08:
    """Verify config loader handles S08 fields."""

    def test_earnings_config_default(self):
        """Default EarningsConfig uses 14-day exclusion."""
        config = EarningsConfig()
        assert config.earnings_exclusion_days == 14

    def test_earnings_config_validation(self):
        """Negative earnings_exclusion_days raises ValueError."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            EarningsConfig(earnings_exclusion_days=-1)

    def test_screener_config_has_earnings(self):
        """ScreenerConfig includes earnings section."""
        config = ScreenerConfig()
        assert hasattr(config, "earnings")
        assert isinstance(config.earnings, EarningsConfig)

    def test_load_config_with_earnings(self, tmp_path):
        """Config file with earnings section loads correctly."""
        config_file = tmp_path / "screener.yaml"
        config_file.write_text(
            "preset: moderate\n"
            "earnings:\n"
            "  earnings_exclusion_days: 21\n"
        )
        config = load_config(str(config_file))
        assert config.earnings.earnings_exclusion_days == 21

    def test_load_config_preset_earnings_defaults(self, tmp_path):
        """Loading preset without overrides gets preset's earnings values."""
        config_file = tmp_path / "screener.yaml"
        config_file.write_text("preset: conservative\n")
        config = load_config(str(config_file))
        assert config.earnings.earnings_exclusion_days == 21

    def test_hv_percentile_min_in_loaded_config(self, tmp_path):
        """HV percentile min is loaded from preset."""
        config_file = tmp_path / "screener.yaml"
        config_file.write_text("preset: conservative\n")
        config = load_config(str(config_file))
        assert config.technicals.hv_percentile_min == 50


# ---------------------------------------------------------------------------
# Stage 1 filter integration (HV percentile included)
# ---------------------------------------------------------------------------


class TestStage1WithHvPercentile:
    """Verify run_stage_1_filters includes hv_percentile."""

    def _config(self) -> ScreenerConfig:
        return ScreenerConfig(
            technicals=TechnicalsConfig(
                price_min=5.0,
                price_max=500.0,
                avg_volume_min=100000,
                rsi_max=80.0,
                above_sma200=False,
                hv_percentile_min=20.0,
            ),
        )

    def test_stage1_includes_hv_percentile_filter(self):
        """Stage 1 should now run 5 filters including hv_percentile."""
        stock = ScreenedStock.from_symbol("AAPL")
        stock.price = 150.0
        stock.avg_volume = 1_000_000
        stock.rsi_14 = 50.0
        stock.above_sma200 = True
        stock.hv_percentile = 45.0

        config = self._config()
        passed = run_stage_1_filters(stock, config)

        assert passed is True
        filter_names = [r.filter_name for r in stock.filter_results]
        assert "hv_percentile" in filter_names

    def test_stage1_fails_on_low_hv_percentile(self):
        """Stage 1 should fail if hv_percentile is below threshold."""
        stock = ScreenedStock.from_symbol("AAPL")
        stock.price = 150.0
        stock.avg_volume = 1_000_000
        stock.rsi_14 = 50.0
        stock.above_sma200 = True
        stock.hv_percentile = 10.0  # Below 20.0 threshold

        config = self._config()
        passed = run_stage_1_filters(stock, config)

        assert passed is False
        hv_result = [r for r in stock.filter_results if r.filter_name == "hv_percentile"][0]
        assert hv_result.passed is False
