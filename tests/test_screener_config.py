"""Tests for screener config loading, preset profiles, and ScreenedStock model."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from models.screened_stock import FilterResult, ScreenedStock
from screener.config_loader import (
    FundamentalsConfig,
    OptionsConfig,
    ScreenerConfig,
    SectorsConfig,
    TechnicalsConfig,
    deep_merge,
    format_validation_errors,
    load_config,
    load_preset,
)


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
        assert fund["debt_equity_max"] == 1.5
        assert fund["net_margin_min"] == 0
        assert fund["sales_growth_min"] == 5

        assert tech["price_min"] == 10
        assert tech["price_max"] == 200
        assert tech["avg_volume_min"] == 500000
        assert tech["rsi_max"] == 65
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
        assert fund["debt_equity_max"] == 3.0
        assert fund["net_margin_min"] == -10
        assert fund["sales_growth_min"] == -5

    def test_all_presets_have_differentiated_technicals(self):
        """Presets should have differentiated technical thresholds (S07 overhaul)."""
        conservative = self._load_preset("conservative")
        moderate = self._load_preset("moderate")
        aggressive = self._load_preset("aggressive")

        # avg_volume_min is differentiated across presets (FIX-04)
        assert conservative["technicals"]["avg_volume_min"] == 1000000
        assert moderate["technicals"]["avg_volume_min"] == 500000
        assert aggressive["technicals"]["avg_volume_min"] == 200000

        # rsi_max is differentiated
        assert conservative["technicals"]["rsi_max"] < aggressive["technicals"]["rsi_max"]

        # above_sma200 is relaxed for aggressive
        assert conservative["technicals"]["above_sma200"] is True
        assert aggressive["technicals"]["above_sma200"] is False


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


# ---------------------------------------------------------------------------
# Config loader tests (Task 2)
# ---------------------------------------------------------------------------


class TestLoadPreset:
    """Verify load_preset function reads preset YAML files correctly."""

    def test_load_preset_moderate_via_function(self):
        data = load_preset("moderate")
        assert data["fundamentals"]["market_cap_min"] == 2000000000
        assert data["preset"] == "moderate"

    def test_load_preset_conservative_via_function(self):
        data = load_preset("conservative")
        assert data["fundamentals"]["market_cap_min"] == 10000000000

    def test_load_preset_aggressive_via_function(self):
        data = load_preset("aggressive")
        assert data["fundamentals"]["market_cap_min"] == 500000000

    def test_load_preset_invalid_name(self):
        with pytest.raises(FileNotFoundError, match="yolo"):
            load_preset("yolo")


class TestDeepMerge:
    """Verify recursive deep merge behavior."""

    def test_deep_merge_flat(self):
        base = {"a": 1, "b": 2}
        overrides = {"b": 3, "c": 4}
        result = deep_merge(base, overrides)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        overrides = {"a": {"x": 10}}
        result = deep_merge(base, overrides)
        assert result == {"a": {"x": 10, "y": 2}, "b": 3}

    def test_deep_merge_does_not_mutate_base(self):
        base = {"a": {"x": 1}}
        overrides = {"a": {"x": 10}}
        deep_merge(base, overrides)
        assert base["a"]["x"] == 1


class TestLoadConfig:
    """Verify load_config loads, merges, validates, and auto-generates."""

    def test_load_valid_config(self, tmp_path):
        """load_config with a valid screener.yaml returns ScreenerConfig with correct values."""
        config_file = tmp_path / "screener.yaml"
        config_file.write_text(
            "preset: moderate\n"
            "fundamentals:\n"
            "  market_cap_min: 5000000000\n"
        )
        config = load_config(str(config_file))
        assert isinstance(config, ScreenerConfig)
        assert config.fundamentals.market_cap_min == 5000000000
        assert config.preset == "moderate"

    def test_deep_merge_overrides(self, tmp_path):
        """Overriding one field keeps all other moderate preset values intact."""
        config_file = tmp_path / "screener.yaml"
        config_file.write_text(
            "preset: moderate\n"
            "fundamentals:\n"
            "  market_cap_min: 5000000000\n"
        )
        config = load_config(str(config_file))
        # Override took effect
        assert config.fundamentals.market_cap_min == 5000000000
        # Other moderate preset values preserved
        assert config.fundamentals.debt_equity_max == 1.5
        assert config.fundamentals.net_margin_min == 0
        assert config.fundamentals.sales_growth_min == 5

    def test_deep_merge_preserves_nested(self, tmp_path):
        """Overriding one field in technicals does not clobber other technicals fields."""
        config_file = tmp_path / "screener.yaml"
        config_file.write_text(
            "preset: moderate\n"
            "technicals:\n"
            "  price_max: 100\n"
        )
        config = load_config(str(config_file))
        assert config.technicals.price_max == 100
        # Other technicals preserved from preset
        assert config.technicals.price_min == 10
        assert config.technicals.avg_volume_min == 500000
        assert config.technicals.rsi_max == 65
        assert config.technicals.above_sma200 is True

    def test_auto_generate_missing_config(self, tmp_path):
        """When screener.yaml does not exist, load_config auto-generates it with moderate preset."""
        config_file = tmp_path / "screener.yaml"
        assert not config_file.exists()

        config = load_config(str(config_file))
        # File was created
        assert config_file.exists()
        # Returns valid config with moderate defaults
        assert isinstance(config, ScreenerConfig)
        assert config.preset == "moderate"
        assert config.fundamentals.market_cap_min == 2000000000

    def test_preset_selection(self, tmp_path):
        """screener.yaml with preset: conservative loads conservative values as base."""
        config_file = tmp_path / "screener.yaml"
        config_file.write_text("preset: conservative\n")
        config = load_config(str(config_file))
        assert config.preset == "conservative"
        assert config.fundamentals.market_cap_min == 10000000000
        assert config.fundamentals.debt_equity_max == 0.5

    def test_validation_error_wrong_type(self, tmp_path):
        """screener.yaml with fundamentals.market_cap_min: 'not_a_number' raises ValidationError."""
        config_file = tmp_path / "screener.yaml"
        config_file.write_text(
            "preset: moderate\n"
            "fundamentals:\n"
            "  market_cap_min: not_a_number\n"
        )
        with pytest.raises(ValidationError):
            load_config(str(config_file))

    def test_validation_error_out_of_range(self, tmp_path):
        """screener.yaml with fundamentals.debt_equity_max: -1 raises ValidationError."""
        config_file = tmp_path / "screener.yaml"
        config_file.write_text(
            "preset: moderate\n"
            "fundamentals:\n"
            "  debt_equity_max: -1\n"
        )
        with pytest.raises(ValidationError):
            load_config(str(config_file))

    def test_validation_error_invalid_preset(self, tmp_path):
        """screener.yaml with preset: 'yolo' raises ValidationError mentioning valid presets."""
        config_file = tmp_path / "screener.yaml"
        config_file.write_text("preset: yolo\n")
        with pytest.raises(ValidationError, match="conservative.*moderate.*aggressive|preset"):
            load_config(str(config_file))


class TestFormatValidationErrors:
    """Verify validation error formatting for user-friendly messages."""

    def test_format_validation_errors(self):
        """ValidationError errors are formatted with field name and human-readable message."""
        try:
            ScreenerConfig.model_validate({
                "preset": "moderate",
                "fundamentals": {"debt_equity_max": -1},
                "technicals": {"price_min": 10, "price_max": 50, "avg_volume_min": 2000000, "rsi_max": 60, "above_sma200": True},
                "options": {"optionable": True},
                "sectors": {"include": [], "exclude": []},
            })
            pytest.fail("Expected ValidationError")
        except ValidationError as e:
            formatted = format_validation_errors(e)
            assert "debt_equity_max" in formatted
            # Should contain a human-readable message
            assert len(formatted) > 10
