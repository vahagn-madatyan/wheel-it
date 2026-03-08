"""Tests for screener config loading, preset profiles, and ScreenedStock model."""

from pathlib import Path

import pytest
import yaml

from models.screened_stock import FilterResult, ScreenedStock


PRESETS_DIR = Path(__file__).resolve().parent.parent / "config" / "presets"


# ---------------------------------------------------------------------------
# Preset loading tests (Task 1 -- read YAML files directly)
# ---------------------------------------------------------------------------


class TestPresetLoading:
    """Verify preset YAML files contain correct threshold values."""

    def _load_preset(self, name: str) -> dict:
        with open(PRESETS_DIR / f"{name}.yaml") as f:
            return yaml.safe_load(f)

    def test_load_preset_moderate(self):
        data = self._load_preset("moderate")
        fund = data["fundamentals"]
        tech = data["technicals"]

        assert fund["market_cap_min"] == 2000000000
        assert fund["debt_equity_max"] == 1.0
        assert fund["net_margin_min"] == 0
        assert fund["sales_growth_min"] == 5

        assert tech["price_min"] == 10
        assert tech["price_max"] == 50
        assert tech["avg_volume_min"] == 2000000
        assert tech["rsi_max"] == 60
        assert tech["above_sma200"] is True

    def test_load_preset_conservative(self):
        data = self._load_preset("conservative")
        fund = data["fundamentals"]

        assert fund["market_cap_min"] == 10000000000
        assert fund["debt_equity_max"] == 0.5
        assert fund["net_margin_min"] == 10
        assert fund["sales_growth_min"] == 10

    def test_load_preset_aggressive(self):
        data = self._load_preset("aggressive")
        fund = data["fundamentals"]

        assert fund["market_cap_min"] == 500000000
        assert fund["debt_equity_max"] == 2.0
        assert fund["net_margin_min"] == -5
        assert fund["sales_growth_min"] == 0

    def test_all_presets_share_technical_values(self):
        """All three presets must have identical technicals section."""
        presets = [self._load_preset(name) for name in ("conservative", "moderate", "aggressive")]
        techs = [p["technicals"] for p in presets]

        expected = {
            "price_min": 10,
            "price_max": 50,
            "avg_volume_min": 2000000,
            "rsi_max": 60,
            "above_sma200": True,
        }

        for tech in techs:
            for key, value in expected.items():
                assert tech[key] == value, f"Preset technical mismatch on {key}"


# ---------------------------------------------------------------------------
# ScreenedStock model tests (Task 1)
# ---------------------------------------------------------------------------


class TestScreenedStock:
    """Verify ScreenedStock dataclass behavior."""

    def test_screened_stock_from_symbol(self):
        stock = ScreenedStock.from_symbol("AAPL")
        assert stock.symbol == "AAPL"
        assert stock.price is None
        assert stock.avg_volume is None
        assert stock.market_cap is None
        assert stock.debt_equity is None
        assert stock.net_margin is None
        assert stock.sales_growth is None
        assert stock.sector is None
        assert stock.industry is None
        assert stock.rsi_14 is None
        assert stock.sma_200 is None
        assert stock.above_sma200 is None
        assert stock.is_optionable is None
        assert stock.score is None
        assert stock.filter_results == []
        assert stock.raw_finnhub_profile is None
        assert stock.raw_finnhub_metrics is None
        assert stock.raw_alpaca_bars is None

    def test_screened_stock_from_symbol_uppercases(self):
        stock = ScreenedStock.from_symbol("aapl")
        assert stock.symbol == "AAPL"

    def test_screened_stock_passed_all_filters_empty(self):
        """Empty filter_results means not yet filtered -- returns False."""
        stock = ScreenedStock.from_symbol("AAPL")
        assert stock.passed_all_filters is False

    def test_screened_stock_passed_all_filters_mixed(self):
        """With mixed FilterResults, passed_all_filters returns False."""
        stock = ScreenedStock.from_symbol("AAPL")
        stock.filter_results = [
            FilterResult(filter_name="market_cap", passed=True, actual_value=5e9, threshold=2e9),
            FilterResult(filter_name="debt_equity", passed=False, actual_value=1.5, threshold=1.0, reason="Too high"),
        ]
        assert stock.passed_all_filters is False

    def test_screened_stock_passed_all_filters_all_passing(self):
        """With all passing FilterResults, passed_all_filters returns True."""
        stock = ScreenedStock.from_symbol("AAPL")
        stock.filter_results = [
            FilterResult(filter_name="market_cap", passed=True, actual_value=5e9, threshold=2e9),
            FilterResult(filter_name="debt_equity", passed=True, actual_value=0.5, threshold=1.0),
        ]
        assert stock.passed_all_filters is True

    def test_screened_stock_failed_filters(self):
        """Returns only the FilterResult entries where passed=False."""
        stock = ScreenedStock.from_symbol("AAPL")
        f1 = FilterResult(filter_name="market_cap", passed=True)
        f2 = FilterResult(filter_name="debt_equity", passed=False, reason="Too high")
        f3 = FilterResult(filter_name="net_margin", passed=False, reason="Negative")
        stock.filter_results = [f1, f2, f3]

        failed = stock.failed_filters
        assert len(failed) == 2
        assert f2 in failed
        assert f3 in failed
        assert f1 not in failed
