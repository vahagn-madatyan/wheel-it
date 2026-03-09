"""Tests for screener.pipeline — filter functions, HV computation, and stage runners."""

import logging as stdlib_logging
import math
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from models.screened_stock import ScreenedStock, FilterResult
from screener.config_loader import ScreenerConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stock(**kwargs) -> ScreenedStock:
    """Create a ScreenedStock with custom fields set."""
    stock = ScreenedStock.from_symbol(kwargs.pop("symbol", "TEST"))
    for k, v in kwargs.items():
        setattr(stock, k, v)
    return stock


def _default_config(**overrides) -> ScreenerConfig:
    """Create a ScreenerConfig with defaults, applying overrides."""
    return ScreenerConfig.model_validate(overrides) if overrides else ScreenerConfig()


# ===========================================================================
# TestFilterPriceRange
# ===========================================================================

class TestFilterPriceRange:
    """filter_price_range: pass/fail/None cases."""

    def test_price_within_range_passes(self):
        from screener.pipeline import filter_price_range
        stock = _make_stock(price=25.0)
        config = _default_config()
        result = filter_price_range(stock, config)
        assert result.passed is True
        assert result.filter_name == "price_range"
        assert result.actual_value == 25.0
        assert result.reason == ""

    def test_price_below_min_fails(self):
        from screener.pipeline import filter_price_range
        stock = _make_stock(price=5.0)
        config = _default_config()
        result = filter_price_range(stock, config)
        assert result.passed is False
        assert result.actual_value == 5.0
        assert result.threshold == config.technicals.price_min
        assert "below" in result.reason.lower() or "min" in result.reason.lower()

    def test_price_above_max_fails(self):
        from screener.pipeline import filter_price_range
        stock = _make_stock(price=100.0)
        config = _default_config()
        result = filter_price_range(stock, config)
        assert result.passed is False
        assert result.actual_value == 100.0
        assert "above" in result.reason.lower() or "max" in result.reason.lower()

    def test_price_none_fails(self):
        from screener.pipeline import filter_price_range
        stock = _make_stock(price=None)
        config = _default_config()
        result = filter_price_range(stock, config)
        assert result.passed is False
        assert "unavailable" in result.reason.lower()


# ===========================================================================
# TestFilterAvgVolume
# ===========================================================================

class TestFilterAvgVolume:
    """filter_avg_volume: pass/fail/None cases."""

    def test_volume_above_min_passes(self):
        from screener.pipeline import filter_avg_volume
        stock = _make_stock(avg_volume=3_000_000)
        config = _default_config()
        result = filter_avg_volume(stock, config)
        assert result.passed is True
        assert result.filter_name == "avg_volume"

    def test_volume_below_min_fails(self):
        from screener.pipeline import filter_avg_volume
        stock = _make_stock(avg_volume=500_000)
        config = _default_config()
        result = filter_avg_volume(stock, config)
        assert result.passed is False
        assert result.actual_value == 500_000
        assert result.threshold == config.technicals.avg_volume_min

    def test_volume_none_fails(self):
        from screener.pipeline import filter_avg_volume
        stock = _make_stock(avg_volume=None)
        config = _default_config()
        result = filter_avg_volume(stock, config)
        assert result.passed is False
        assert "unavailable" in result.reason.lower()


# ===========================================================================
# TestFilterRSI
# ===========================================================================

class TestFilterRSI:
    """filter_rsi: pass/fail/None cases."""

    def test_rsi_below_max_passes(self):
        from screener.pipeline import filter_rsi
        stock = _make_stock(rsi_14=45.0)
        config = _default_config()
        result = filter_rsi(stock, config)
        assert result.passed is True
        assert result.filter_name == "rsi"

    def test_rsi_above_max_fails(self):
        from screener.pipeline import filter_rsi
        stock = _make_stock(rsi_14=75.0)
        config = _default_config()
        result = filter_rsi(stock, config)
        assert result.passed is False
        assert result.actual_value == 75.0
        assert result.threshold == config.technicals.rsi_max

    def test_rsi_none_fails(self):
        from screener.pipeline import filter_rsi
        stock = _make_stock(rsi_14=None)
        config = _default_config()
        result = filter_rsi(stock, config)
        assert result.passed is False
        assert "unavailable" in result.reason.lower()


# ===========================================================================
# TestFilterSMA200
# ===========================================================================

class TestFilterSMA200:
    """filter_sma200: pass/fail/None/disabled cases."""

    def test_above_sma200_passes(self):
        from screener.pipeline import filter_sma200
        stock = _make_stock(above_sma200=True)
        config = _default_config()
        result = filter_sma200(stock, config)
        assert result.passed is True
        assert result.filter_name == "sma200"

    def test_below_sma200_fails(self):
        from screener.pipeline import filter_sma200
        stock = _make_stock(above_sma200=False)
        config = _default_config()
        result = filter_sma200(stock, config)
        assert result.passed is False

    def test_sma200_none_fails(self):
        from screener.pipeline import filter_sma200
        stock = _make_stock(above_sma200=None)
        config = _default_config()
        result = filter_sma200(stock, config)
        assert result.passed is False
        assert "unavailable" in result.reason.lower()

    def test_sma200_disabled_passes(self):
        from screener.pipeline import filter_sma200
        stock = _make_stock(above_sma200=False)
        config = ScreenerConfig.model_validate({"technicals": {"above_sma200": False}})
        result = filter_sma200(stock, config)
        assert result.passed is True


# ===========================================================================
# TestFilterMarketCap
# ===========================================================================

class TestFilterMarketCap:
    """filter_market_cap: pass/fail/None cases."""

    def test_market_cap_above_min_passes(self):
        from screener.pipeline import filter_market_cap
        stock = _make_stock(market_cap=5_000_000_000)
        config = _default_config()
        result = filter_market_cap(stock, config)
        assert result.passed is True
        assert result.filter_name == "market_cap"

    def test_market_cap_below_min_fails(self):
        from screener.pipeline import filter_market_cap
        stock = _make_stock(market_cap=500_000_000)
        config = _default_config()
        result = filter_market_cap(stock, config)
        assert result.passed is False
        assert result.actual_value == 500_000_000
        assert result.threshold == config.fundamentals.market_cap_min

    def test_market_cap_none_fails(self):
        from screener.pipeline import filter_market_cap
        stock = _make_stock(market_cap=None)
        config = _default_config()
        result = filter_market_cap(stock, config)
        assert result.passed is False
        assert "unavailable" in result.reason.lower()


# ===========================================================================
# TestFilterDebtEquity
# ===========================================================================

class TestFilterDebtEquity:
    """filter_debt_equity: pass/fail/None cases."""

    def test_debt_equity_below_max_passes(self):
        from screener.pipeline import filter_debt_equity
        stock = _make_stock(debt_equity=0.5)
        config = _default_config()
        result = filter_debt_equity(stock, config)
        assert result.passed is True
        assert result.filter_name == "debt_equity"

    def test_debt_equity_above_max_fails(self):
        from screener.pipeline import filter_debt_equity
        stock = _make_stock(debt_equity=2.5)
        config = _default_config()
        result = filter_debt_equity(stock, config)
        assert result.passed is False
        assert result.actual_value == 2.5
        assert result.threshold == config.fundamentals.debt_equity_max

    def test_debt_equity_none_fails(self):
        from screener.pipeline import filter_debt_equity
        stock = _make_stock(debt_equity=None)
        config = _default_config()
        result = filter_debt_equity(stock, config)
        assert result.passed is False
        assert "unavailable" in result.reason.lower()


# ===========================================================================
# TestFilterNetMargin
# ===========================================================================

class TestFilterNetMargin:
    """filter_net_margin: pass/fail/None cases."""

    def test_net_margin_above_min_passes(self):
        from screener.pipeline import filter_net_margin
        stock = _make_stock(net_margin=10.0)
        config = _default_config()
        result = filter_net_margin(stock, config)
        assert result.passed is True
        assert result.filter_name == "net_margin"

    def test_net_margin_below_min_fails(self):
        from screener.pipeline import filter_net_margin
        stock = _make_stock(net_margin=-5.0)
        config = _default_config()
        result = filter_net_margin(stock, config)
        assert result.passed is False
        assert result.actual_value == -5.0
        assert result.threshold == config.fundamentals.net_margin_min

    def test_net_margin_none_fails(self):
        from screener.pipeline import filter_net_margin
        stock = _make_stock(net_margin=None)
        config = _default_config()
        result = filter_net_margin(stock, config)
        assert result.passed is False
        assert "unavailable" in result.reason.lower()


# ===========================================================================
# TestFilterSalesGrowth
# ===========================================================================

class TestFilterSalesGrowth:
    """filter_sales_growth: pass/fail/None cases."""

    def test_sales_growth_above_min_passes(self):
        from screener.pipeline import filter_sales_growth
        stock = _make_stock(sales_growth=10.0)
        config = _default_config()
        result = filter_sales_growth(stock, config)
        assert result.passed is True
        assert result.filter_name == "sales_growth"

    def test_sales_growth_below_min_fails(self):
        from screener.pipeline import filter_sales_growth
        stock = _make_stock(sales_growth=2.0)
        config = _default_config()
        result = filter_sales_growth(stock, config)
        assert result.passed is False
        assert result.actual_value == 2.0
        assert result.threshold == config.fundamentals.sales_growth_min

    def test_sales_growth_none_fails(self):
        from screener.pipeline import filter_sales_growth
        stock = _make_stock(sales_growth=None)
        config = _default_config()
        result = filter_sales_growth(stock, config)
        assert result.passed is False
        assert "unavailable" in result.reason.lower()


# ===========================================================================
# TestFilterSector
# ===========================================================================

class TestFilterSector:
    """filter_sector: include/exclude/None cases."""

    def test_sector_in_include_list_passes(self):
        from screener.pipeline import filter_sector
        stock = _make_stock(sector="Technology")
        config = ScreenerConfig.model_validate({"sectors": {"include": ["Technology", "Healthcare"]}})
        result = filter_sector(stock, config)
        assert result.passed is True
        assert result.filter_name == "sector"

    def test_sector_case_insensitive_include(self):
        from screener.pipeline import filter_sector
        stock = _make_stock(sector="technology")
        config = ScreenerConfig.model_validate({"sectors": {"include": ["Technology"]}})
        result = filter_sector(stock, config)
        assert result.passed is True

    def test_empty_include_not_in_exclude_passes(self):
        from screener.pipeline import filter_sector
        stock = _make_stock(sector="Technology")
        config = ScreenerConfig.model_validate({"sectors": {"include": [], "exclude": ["Utilities"]}})
        result = filter_sector(stock, config)
        assert result.passed is True

    def test_sector_in_exclude_list_fails(self):
        from screener.pipeline import filter_sector
        stock = _make_stock(sector="Utilities")
        config = ScreenerConfig.model_validate({"sectors": {"exclude": ["utilities"]}})
        result = filter_sector(stock, config)
        assert result.passed is False

    def test_sector_none_fails(self):
        from screener.pipeline import filter_sector
        stock = _make_stock(sector=None)
        config = _default_config()
        result = filter_sector(stock, config)
        assert result.passed is False
        assert "unavailable" in result.reason.lower()


# ===========================================================================
# TestFilterOptionable
# ===========================================================================

class TestFilterOptionable:
    """filter_optionable: in set/not in set/disabled cases."""

    def test_symbol_in_optionable_set_passes(self):
        from screener.pipeline import filter_optionable
        stock = _make_stock(symbol="AAPL")
        config = _default_config()
        result = filter_optionable(stock, config, optionable_set={"AAPL", "MSFT"})
        assert result.passed is True
        assert result.filter_name == "optionable"

    def test_symbol_not_in_optionable_set_fails(self):
        from screener.pipeline import filter_optionable
        stock = _make_stock(symbol="XYZ")
        config = _default_config()
        result = filter_optionable(stock, config, optionable_set={"AAPL", "MSFT"})
        assert result.passed is False

    def test_optionable_disabled_passes(self):
        from screener.pipeline import filter_optionable
        stock = _make_stock(symbol="XYZ")
        config = ScreenerConfig.model_validate({"options": {"optionable": False}})
        result = filter_optionable(stock, config, optionable_set=set())
        assert result.passed is True


# ===========================================================================
# TestComputeHistoricalVolatility
# ===========================================================================

class TestComputeHistoricalVolatility:
    """compute_historical_volatility: sufficient data / insufficient data."""

    def test_hv_returns_annualized_float(self):
        from screener.pipeline import compute_historical_volatility
        # Generate 60 days of synthetic close prices with known pattern
        np.random.seed(42)
        prices = 100 * np.exp(np.cumsum(np.random.normal(0, 0.02, 60)))
        df = pd.DataFrame({"close": prices})
        result = compute_historical_volatility(df, window=30)
        assert result is not None
        assert isinstance(result, float)
        assert result > 0
        # Annualized HV should be in a reasonable range (0.01 to 5.0)
        assert 0.01 < result < 5.0

    def test_hv_returns_none_insufficient_data(self):
        from screener.pipeline import compute_historical_volatility
        # Only 20 data points, need window+1 = 31
        df = pd.DataFrame({"close": [100 + i for i in range(20)]})
        result = compute_historical_volatility(df, window=30)
        assert result is None


# ===========================================================================
# TestRunStage1Filters
# ===========================================================================

class TestRunStage1Filters:
    """run_stage_1_filters: orchestrates 4 Stage 1 filters."""

    def test_all_pass_returns_true(self):
        from screener.pipeline import run_stage_1_filters
        stock = _make_stock(price=25.0, avg_volume=3_000_000, rsi_14=45.0, above_sma200=True)
        config = _default_config()
        result = run_stage_1_filters(stock, config)
        assert result is True
        assert len(stock.filter_results) == 4
        assert all(r.passed for r in stock.filter_results)

    def test_some_fail_returns_false_records_all(self):
        from screener.pipeline import run_stage_1_filters
        stock = _make_stock(price=5.0, avg_volume=3_000_000, rsi_14=75.0, above_sma200=True)
        config = _default_config()
        result = run_stage_1_filters(stock, config)
        assert result is False
        # Should still have 4 filter results (all run even when some fail)
        assert len(stock.filter_results) == 4
        filter_names = {r.filter_name for r in stock.filter_results}
        assert "price_range" in filter_names
        assert "avg_volume" in filter_names
        assert "rsi" in filter_names
        assert "sma200" in filter_names


# ===========================================================================
# TestRunStage2Filters
# ===========================================================================

class TestRunStage2Filters:
    """run_stage_2_filters: fetches Finnhub data, populates fields, runs 6 filters."""

    def test_all_pass_returns_true(self):
        from screener.pipeline import run_stage_2_filters

        stock = _make_stock(symbol="AAPL")
        config = _default_config()

        mock_finnhub = MagicMock()
        mock_finnhub.company_profile.return_value = {
            "marketCapitalization": 2800000,  # in millions
            "finnhubIndustry": "Technology",
        }
        mock_finnhub.company_metrics.return_value = {
            "metric": {
                "totalDebtToEquity": 0.5,
                "netProfitMarginTTM": 25.0,
                "revenueGrowthQuarterlyYoy": 10.0,
            }
        }

        optionable_set = {"AAPL"}
        # Use a config that allows Technology sector
        config_with_sectors = ScreenerConfig.model_validate({
            "sectors": {"include": [], "exclude": []},
        })

        result = run_stage_2_filters(stock, config_with_sectors, mock_finnhub, optionable_set)
        assert result is True
        # Should have 6 filter results
        assert len(stock.filter_results) == 6
        # Verify Finnhub data was populated on the stock
        assert stock.market_cap == 2_800_000_000_000  # 2800000 * 1_000_000
        assert stock.debt_equity == 0.5
        assert stock.net_margin == 25.0
        assert stock.sales_growth == 10.0
        assert stock.sector == "Technology"

    def test_empty_profile_fails_all(self):
        from screener.pipeline import run_stage_2_filters

        stock = _make_stock(symbol="INVALID")
        config = _default_config()

        mock_finnhub = MagicMock()
        mock_finnhub.company_profile.return_value = {}
        mock_finnhub.company_metrics.return_value = {"metric": {}}

        result = run_stage_2_filters(stock, config, mock_finnhub, set())
        assert result is False
        # Should still have filter results recorded
        failed = [r for r in stock.filter_results if not r.passed]
        assert len(failed) > 0


# ===========================================================================
# Scoring helpers
# ===========================================================================

def _make_scored_stocks(specs: list[dict]) -> list[ScreenedStock]:
    """Build a list of ScreenedStock objects for scoring tests.

    Each spec dict is passed to _make_stock. Returns the list for use
    as ``all_passing_stocks`` parameter to ``compute_wheel_score``.
    """
    return [_make_stock(**spec) for spec in specs]


# ===========================================================================
# TestComputeWheelScore
# ===========================================================================

class TestComputeWheelScore:
    """compute_wheel_score: weighted scoring with 3 components."""

    def test_score_returns_float_in_0_100(self):
        from screener.pipeline import compute_wheel_score

        stocks = _make_scored_stocks([
            {"symbol": "A", "price": 20.0, "hv_30": 0.4, "net_margin": 15.0, "sales_growth": 10.0, "debt_equity": 0.3},
            {"symbol": "B", "price": 40.0, "hv_30": 0.2, "net_margin": 5.0, "sales_growth": 5.0, "debt_equity": 0.8},
        ])
        score = compute_wheel_score(stocks[0], stocks)
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_score_capital_efficiency_higher_for_lower_price(self):
        from screener.pipeline import compute_wheel_score

        stocks = _make_scored_stocks([
            {"symbol": "CHEAP", "price": 15.0, "hv_30": 0.3, "net_margin": 10.0, "sales_growth": 10.0, "debt_equity": 0.5},
            {"symbol": "PRICEY", "price": 45.0, "hv_30": 0.3, "net_margin": 10.0, "sales_growth": 10.0, "debt_equity": 0.5},
        ])
        score_cheap = compute_wheel_score(stocks[0], stocks)
        score_pricey = compute_wheel_score(stocks[1], stocks)
        assert score_cheap > score_pricey

    def test_score_volatility_higher_for_higher_hv(self):
        from screener.pipeline import compute_wheel_score

        stocks = _make_scored_stocks([
            {"symbol": "HI_HV", "price": 25.0, "hv_30": 0.6, "net_margin": 10.0, "sales_growth": 10.0, "debt_equity": 0.5},
            {"symbol": "LO_HV", "price": 25.0, "hv_30": 0.2, "net_margin": 10.0, "sales_growth": 10.0, "debt_equity": 0.5},
        ])
        score_hi = compute_wheel_score(stocks[0], stocks)
        score_lo = compute_wheel_score(stocks[1], stocks)
        assert score_hi > score_lo

    def test_score_fundamentals_higher_for_strong_fundamentals(self):
        from screener.pipeline import compute_wheel_score

        stocks = _make_scored_stocks([
            {"symbol": "STRONG", "price": 25.0, "hv_30": 0.3, "net_margin": 25.0, "sales_growth": 20.0, "debt_equity": 0.1},
            {"symbol": "WEAK", "price": 25.0, "hv_30": 0.3, "net_margin": 2.0, "sales_growth": 1.0, "debt_equity": 0.9},
        ])
        score_strong = compute_wheel_score(stocks[0], stocks)
        score_weak = compute_wheel_score(stocks[1], stocks)
        assert score_strong > score_weak

    def test_score_none_hv_gets_neutral_volatility(self):
        from screener.pipeline import compute_wheel_score

        stocks = _make_scored_stocks([
            {"symbol": "NONE_HV", "price": 25.0, "hv_30": None, "net_margin": 10.0, "sales_growth": 10.0, "debt_equity": 0.5},
            {"symbol": "HI_HV", "price": 25.0, "hv_30": 0.8, "net_margin": 10.0, "sales_growth": 10.0, "debt_equity": 0.5},
            {"symbol": "LO_HV", "price": 25.0, "hv_30": 0.1, "net_margin": 10.0, "sales_growth": 10.0, "debt_equity": 0.5},
        ])
        score_none = compute_wheel_score(stocks[0], stocks)
        # Should not error and should return a valid score
        assert isinstance(score_none, float)
        assert 0 <= score_none <= 100

    def test_score_none_fundamentals_gets_neutral(self):
        from screener.pipeline import compute_wheel_score

        stocks = _make_scored_stocks([
            {"symbol": "NO_FUND", "price": 25.0, "hv_30": 0.3, "net_margin": None, "sales_growth": None, "debt_equity": None},
            {"symbol": "OTHER", "price": 30.0, "hv_30": 0.3, "net_margin": 10.0, "sales_growth": 10.0, "debt_equity": 0.5},
        ])
        score = compute_wheel_score(stocks[0], stocks)
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_score_weights_sum_to_one(self):
        from screener.pipeline import WEIGHT_CAPITAL_EFFICIENCY, WEIGHT_VOLATILITY, WEIGHT_FUNDAMENTALS

        total = WEIGHT_CAPITAL_EFFICIENCY + WEIGHT_VOLATILITY + WEIGHT_FUNDAMENTALS
        assert abs(total - 1.0) < 1e-9

    def test_score_single_stock_no_division_by_zero(self):
        from screener.pipeline import compute_wheel_score

        stocks = _make_scored_stocks([
            {"symbol": "ONLY", "price": 30.0, "hv_30": 0.4, "net_margin": 15.0, "sales_growth": 10.0, "debt_equity": 0.3},
        ])
        score = compute_wheel_score(stocks[0], stocks)
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_score_identical_stocks_get_identical_scores(self):
        from screener.pipeline import compute_wheel_score

        stocks = _make_scored_stocks([
            {"symbol": "A", "price": 25.0, "hv_30": 0.3, "net_margin": 10.0, "sales_growth": 10.0, "debt_equity": 0.5},
            {"symbol": "B", "price": 25.0, "hv_30": 0.3, "net_margin": 10.0, "sales_growth": 10.0, "debt_equity": 0.5},
        ])
        score_a = compute_wheel_score(stocks[0], stocks)
        score_b = compute_wheel_score(stocks[1], stocks)
        assert score_a == score_b


# ===========================================================================
# TestFetchUniverse
# ===========================================================================

class TestFetchUniverse:
    """fetch_universe: builds universe from Alpaca asset API calls."""

    def test_returns_tuple_of_symbols_and_optionable_set(self):
        from screener.pipeline import fetch_universe

        # Mock asset objects with symbol and tradable attributes
        mock_asset_1 = MagicMock()
        mock_asset_1.symbol = "AAPL"
        mock_asset_1.tradable = True

        mock_asset_2 = MagicMock()
        mock_asset_2.symbol = "MSFT"
        mock_asset_2.tradable = True

        mock_asset_3 = MagicMock()
        mock_asset_3.symbol = "PENNY"
        mock_asset_3.tradable = False  # not tradable

        mock_opt_1 = MagicMock()
        mock_opt_1.symbol = "AAPL"

        mock_trade_client = MagicMock()
        mock_trade_client.get_all_assets.side_effect = [
            [mock_asset_1, mock_asset_2, mock_asset_3],  # Call 1: all assets
            [mock_opt_1],  # Call 2: optionable assets
        ]

        all_symbols, optionable_set = fetch_universe(mock_trade_client)
        assert isinstance(all_symbols, list)
        assert isinstance(optionable_set, set)
        assert "AAPL" in all_symbols
        assert "MSFT" in all_symbols
        assert "PENNY" not in all_symbols  # not tradable
        assert "AAPL" in optionable_set
        assert "MSFT" not in optionable_set

    def test_filters_to_tradable_only(self):
        from screener.pipeline import fetch_universe

        tradable = MagicMock()
        tradable.symbol = "GOOD"
        tradable.tradable = True

        not_tradable = MagicMock()
        not_tradable.symbol = "BAD"
        not_tradable.tradable = False

        mock_trade_client = MagicMock()
        mock_trade_client.get_all_assets.side_effect = [
            [tradable, not_tradable],
            [],
        ]

        all_symbols, _ = fetch_universe(mock_trade_client)
        assert "GOOD" in all_symbols
        assert "BAD" not in all_symbols

    def test_second_call_uses_options_enabled(self):
        from screener.pipeline import fetch_universe

        mock_trade_client = MagicMock()
        mock_trade_client.get_all_assets.side_effect = [[], []]

        fetch_universe(mock_trade_client)
        assert mock_trade_client.get_all_assets.call_count == 2
        # Second call should use attributes="options_enabled"
        second_call_args = mock_trade_client.get_all_assets.call_args_list[1]
        request = second_call_args[0][0]
        assert hasattr(request, "attributes") or "options_enabled" in str(second_call_args)


# ===========================================================================
# TestLoadSymbolList
# ===========================================================================

class TestLoadSymbolList:
    """load_symbol_list: reads symbols from text file."""

    def test_reads_symbols_strips_whitespace_skips_empty(self, tmp_path):
        from screener.pipeline import load_symbol_list

        f = tmp_path / "symbols.txt"
        f.write_text("AAPL\n  MSFT  \n\n# comment\nGOOG\n")
        result = load_symbol_list(str(f))
        assert result == ["AAPL", "MSFT", "GOOG"]

    def test_returns_empty_list_if_file_missing(self, tmp_path):
        from screener.pipeline import load_symbol_list

        result = load_symbol_list(str(tmp_path / "nonexistent.txt"))
        assert result == []


# ===========================================================================
# TestRunPipeline
# ===========================================================================

class TestRunPipeline:
    """run_pipeline: full 3-stage pipeline orchestration."""

    def _setup_mocks(self):
        """Create common mocks for pipeline tests.

        Returns (trade_client, stock_client, finnhub_client, config).
        3 symbols: PASS (passes all), FAILSTG1 (fails Stage 1), NOBAR (no bar data).
        """
        # trade_client: universe with 3 symbols
        asset_pass = MagicMock()
        asset_pass.symbol = "PASS"
        asset_pass.tradable = True

        asset_fail = MagicMock()
        asset_fail.symbol = "FAILSTG1"
        asset_fail.tradable = True

        asset_nobar = MagicMock()
        asset_nobar.symbol = "NOBAR"
        asset_nobar.tradable = True

        opt_pass = MagicMock()
        opt_pass.symbol = "PASS"

        opt_fail = MagicMock()
        opt_fail.symbol = "FAILSTG1"

        opt_nobar = MagicMock()
        opt_nobar.symbol = "NOBAR"

        trade_client = MagicMock()
        trade_client.get_all_assets.side_effect = [
            [asset_pass, asset_fail, asset_nobar],
            [opt_pass, opt_fail, opt_nobar],
        ]

        stock_client = MagicMock()

        # finnhub_client: profile + metrics for PASS symbol
        finnhub_client = MagicMock()
        finnhub_client.company_profile.return_value = {
            "marketCapitalization": 5000,
            "finnhubIndustry": "Technology",
        }
        finnhub_client.company_metrics.return_value = {
            "metric": {
                "totalDebtToEquity": 0.5,
                "netProfitMarginTTM": 15.0,
                "revenueGrowthQuarterlyYoy": 10.0,
            }
        }

        config = ScreenerConfig.model_validate({
            "sectors": {"include": [], "exclude": []},
        })

        return trade_client, stock_client, finnhub_client, config

    def _make_bars_dict(self):
        """Create mock bar data: PASS has valid data, FAILSTG1 has out-of-range price, NOBAR absent."""
        np.random.seed(42)
        # PASS: price in range, good volume -- use 250 data points for SMA
        pass_prices = 25 + np.cumsum(np.random.normal(0, 0.1, 250))
        pass_df = pd.DataFrame({
            "close": pass_prices,
            "volume": [3_000_000] * 250,
        })

        # FAILSTG1: price too low (fails price_range filter)
        fail_prices = 3 + np.cumsum(np.random.normal(0, 0.01, 250))
        fail_df = pd.DataFrame({
            "close": fail_prices,
            "volume": [3_000_000] * 250,
        })

        return {
            "PASS": pass_df,
            "FAILSTG1": fail_df,
            # NOBAR is intentionally absent
        }

    def _make_indicators(self, bars_df):
        """Create mock indicators mimicking compute_indicators output."""
        close = bars_df["close"]
        price = float(close.iloc[-1])
        volume = float(bars_df["volume"].mean())
        return {
            "price": price,
            "avg_volume": volume,
            "rsi_14": 45.0 if price > 10 else 80.0,
            "sma_200": price - 1.0 if price > 10 else price + 5.0,
            "above_sma200": price > 10,
        }

    @patch("screener.pipeline.fetch_daily_bars")
    @patch("screener.pipeline.compute_indicators")
    @patch("screener.pipeline.compute_historical_volatility")
    def test_returns_all_stocks_passing_and_eliminated(
        self, mock_hv, mock_indicators, mock_bars
    ):
        from screener.pipeline import run_pipeline

        trade_client, stock_client, finnhub_client, config = self._setup_mocks()
        bars = self._make_bars_dict()
        mock_bars.return_value = bars

        def side_effect_indicators(df):
            return self._make_indicators(df)

        mock_indicators.side_effect = side_effect_indicators
        mock_hv.return_value = 0.35

        result = run_pipeline(
            trade_client, stock_client, finnhub_client, config,
            symbol_list_path="/nonexistent/path.txt",
        )

        # Should return ALL 3 stocks
        assert len(result) == 3
        symbols = {s.symbol for s in result}
        assert symbols == {"PASS", "FAILSTG1", "NOBAR"}

    @patch("screener.pipeline.fetch_daily_bars")
    @patch("screener.pipeline.compute_indicators")
    @patch("screener.pipeline.compute_historical_volatility")
    def test_stage1_before_stage2(self, mock_hv, mock_indicators, mock_bars):
        from screener.pipeline import run_pipeline

        trade_client, stock_client, finnhub_client, config = self._setup_mocks()
        bars = self._make_bars_dict()
        mock_bars.return_value = bars

        mock_indicators.side_effect = lambda df: self._make_indicators(df)
        mock_hv.return_value = 0.35

        result = run_pipeline(
            trade_client, stock_client, finnhub_client, config,
            symbol_list_path="/nonexistent/path.txt",
        )

        # FAILSTG1 should have Stage 1 filter results but NO Stage 2 results
        fail_stock = next(s for s in result if s.symbol == "FAILSTG1")
        filter_names = {r.filter_name for r in fail_stock.filter_results}
        # Stage 1 names present
        assert "price_range" in filter_names
        # Stage 2 names absent (didn't run because Stage 1 failed)
        assert "market_cap" not in filter_names
        assert "debt_equity" not in filter_names

    @patch("screener.pipeline.fetch_daily_bars")
    @patch("screener.pipeline.compute_indicators")
    @patch("screener.pipeline.compute_historical_volatility")
    def test_no_bar_data_gets_filter_result(self, mock_hv, mock_indicators, mock_bars):
        from screener.pipeline import run_pipeline

        trade_client, stock_client, finnhub_client, config = self._setup_mocks()
        bars = self._make_bars_dict()
        mock_bars.return_value = bars

        mock_indicators.side_effect = lambda df: self._make_indicators(df)
        mock_hv.return_value = 0.35

        result = run_pipeline(
            trade_client, stock_client, finnhub_client, config,
            symbol_list_path="/nonexistent/path.txt",
        )

        nobar_stock = next(s for s in result if s.symbol == "NOBAR")
        assert len(nobar_stock.filter_results) == 1
        assert nobar_stock.filter_results[0].filter_name == "bar_data"
        assert nobar_stock.filter_results[0].passed is False
        assert "No bar data" in nobar_stock.filter_results[0].reason

    @patch("screener.pipeline.fetch_daily_bars")
    @patch("screener.pipeline.compute_indicators")
    @patch("screener.pipeline.compute_historical_volatility")
    def test_only_passing_stocks_scored(self, mock_hv, mock_indicators, mock_bars):
        from screener.pipeline import run_pipeline

        trade_client, stock_client, finnhub_client, config = self._setup_mocks()
        bars = self._make_bars_dict()
        mock_bars.return_value = bars

        mock_indicators.side_effect = lambda df: self._make_indicators(df)
        mock_hv.return_value = 0.35

        result = run_pipeline(
            trade_client, stock_client, finnhub_client, config,
            symbol_list_path="/nonexistent/path.txt",
        )

        # Only PASS should have a score
        pass_stock = next(s for s in result if s.symbol == "PASS")
        assert pass_stock.score is not None
        assert isinstance(pass_stock.score, float)

        # Failed stocks should have no score
        fail_stock = next(s for s in result if s.symbol == "FAILSTG1")
        assert fail_stock.score is None

        nobar_stock = next(s for s in result if s.symbol == "NOBAR")
        assert nobar_stock.score is None

    @patch("screener.pipeline.fetch_daily_bars")
    @patch("screener.pipeline.compute_indicators")
    @patch("screener.pipeline.compute_historical_volatility")
    def test_results_sorted_by_score_descending(self, mock_hv, mock_indicators, mock_bars):
        from screener.pipeline import run_pipeline

        trade_client, stock_client, finnhub_client, config = self._setup_mocks()
        bars = self._make_bars_dict()
        mock_bars.return_value = bars

        mock_indicators.side_effect = lambda df: self._make_indicators(df)
        mock_hv.return_value = 0.35

        result = run_pipeline(
            trade_client, stock_client, finnhub_client, config,
            symbol_list_path="/nonexistent/path.txt",
        )

        # Scored stocks (with score not None) should come first
        scored = [s for s in result if s.score is not None]
        unscored = [s for s in result if s.score is None]
        assert result[:len(scored)] == scored
        assert result[len(scored):] == unscored

        # Scored stocks should be in descending order
        if len(scored) > 1:
            for i in range(len(scored) - 1):
                assert scored[i].score >= scored[i + 1].score

    @patch("screener.pipeline.fetch_daily_bars")
    @patch("screener.pipeline.compute_indicators")
    @patch("screener.pipeline.compute_historical_volatility")
    def test_merges_symbol_list_into_universe(self, mock_hv, mock_indicators, mock_bars, tmp_path):
        from screener.pipeline import run_pipeline

        trade_client, stock_client, finnhub_client, config = self._setup_mocks()

        # Symbol list contains EXTRA symbol not in Alpaca universe
        sym_file = tmp_path / "syms.txt"
        sym_file.write_text("EXTRA\n")

        # Bars dict includes EXTRA
        bars = self._make_bars_dict()
        extra_prices = 25 + np.cumsum(np.random.normal(0, 0.1, 250))
        bars["EXTRA"] = pd.DataFrame({
            "close": extra_prices,
            "volume": [3_000_000] * 250,
        })
        mock_bars.return_value = bars

        mock_indicators.side_effect = lambda df: self._make_indicators(df)
        mock_hv.return_value = 0.35

        result = run_pipeline(
            trade_client, stock_client, finnhub_client, config,
            symbol_list_path=str(sym_file),
        )

        symbols = {s.symbol for s in result}
        assert "EXTRA" in symbols
