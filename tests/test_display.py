"""Tests for screener/display.py -- Rich-formatted screening output."""

import sys
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

# Ensure project root on path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.screened_stock import FilterResult, ScreenedStock
from screener.display import (
    fmt_large_number,
    fmt_pct,
    fmt_price,
    fmt_ratio,
    render_results_table,
    render_stage_summary,
    render_filter_breakdown,
    _score_style,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stock(
    symbol: str,
    filter_results: list[FilterResult] | None = None,
    score: float | None = None,
    price: float | None = None,
    avg_volume: float | None = None,
    market_cap: float | None = None,
    debt_equity: float | None = None,
    net_margin: float | None = None,
    sales_growth: float | None = None,
    rsi_14: float | None = None,
    sector: str | None = None,
) -> ScreenedStock:
    s = ScreenedStock.from_symbol(symbol)
    s.price = price
    s.avg_volume = avg_volume
    s.market_cap = market_cap
    s.debt_equity = debt_equity
    s.net_margin = net_margin
    s.sales_growth = sales_growth
    s.rsi_14 = rsi_14
    s.sector = sector
    s.score = score
    if filter_results is not None:
        s.filter_results = filter_results
    return s


def _all_pass_filters() -> list[FilterResult]:
    """Return filter results where every stage passes."""
    names = [
        "bar_data",
        "price_range", "avg_volume", "rsi", "sma200",
        "market_cap", "debt_equity", "net_margin", "sales_growth", "sector", "optionable",
    ]
    return [FilterResult(filter_name=n, passed=True) for n in names]


def _capture_console() -> Console:
    return Console(file=StringIO(), width=120)


# ===========================================================================
# Formatters
# ===========================================================================


class TestFormatters:
    """Test number formatting helpers."""

    # -- fmt_large_number ---------------------------------------------------

    def test_billions(self):
        assert fmt_large_number(2_100_000_000) == "$2.1B"

    def test_millions(self):
        assert fmt_large_number(3_200_000, prefix="") == "3.2M"

    def test_thousands(self):
        assert fmt_large_number(45_000, prefix="$") == "$45.0K"

    def test_exact_billion(self):
        assert fmt_large_number(1_000_000_000) == "$1.0B"

    def test_sub_thousand(self):
        # Values below 1000 should still render something reasonable
        result = fmt_large_number(500, prefix="$")
        assert "$" in result

    def test_none(self):
        assert fmt_large_number(None) == "N/A"

    def test_zero(self):
        result = fmt_large_number(0)
        assert result is not None  # should not crash

    def test_negative(self):
        result = fmt_large_number(-5_000_000)
        assert "M" in result

    # -- fmt_price ----------------------------------------------------------

    def test_price_normal(self):
        assert fmt_price(24.5) == "$24.50"

    def test_price_none(self):
        assert fmt_price(None) == "N/A"

    def test_price_zero(self):
        assert fmt_price(0) == "$0.00"

    def test_price_high(self):
        assert fmt_price(1234.5) == "$1234.50"

    # -- fmt_pct ------------------------------------------------------------

    def test_pct_normal(self):
        assert fmt_pct(12.345) == "12.3%"

    def test_pct_none(self):
        assert fmt_pct(None) == "N/A"

    def test_pct_zero(self):
        assert fmt_pct(0) == "0.0%"

    def test_pct_negative(self):
        assert fmt_pct(-3.7) == "-3.7%"

    # -- fmt_ratio ----------------------------------------------------------

    def test_ratio_normal(self):
        assert fmt_ratio(0.75) == "0.75"

    def test_ratio_none(self):
        assert fmt_ratio(None) == "N/A"

    def test_ratio_zero(self):
        assert fmt_ratio(0) == "0.00"

    def test_ratio_negative(self):
        assert fmt_ratio(-1.23) == "-1.23"


# ===========================================================================
# Score styling
# ===========================================================================


class TestScoreStyle:
    """Test _score_style color distribution."""

    def test_thirds_distribution(self):
        scores = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
        # Top third -> green, middle -> yellow, bottom -> red
        assert _score_style(60.0, scores) == "green"
        assert _score_style(50.0, scores) == "green"
        assert _score_style(30.0, scores) == "yellow"
        assert _score_style(10.0, scores) == "red"

    def test_single_stock(self):
        assert _score_style(50.0, [50.0]) == "green"

    def test_empty_list(self):
        assert _score_style(50.0, []) == "white"

    def test_two_stocks(self):
        assert _score_style(50.0, [50.0, 30.0]) == "green"
        assert _score_style(30.0, [50.0, 30.0]) == "green"


# ===========================================================================
# Results table rendering
# ===========================================================================


class TestRenderResultsTable:
    """Test render_results_table output."""

    def _make_passing_stocks(self) -> list[ScreenedStock]:
        """Build 3+ passing stocks with varied scores."""
        stocks = []
        for sym, score, price, vol, mcap, de, margin, growth, rsi, sector in [
            ("AAPL", 85.0, 175.50, 50_000_000, 2_800_000_000_000, 1.73, 25.3, 8.1, 55.2, "Technology"),
            ("MSFT", 72.0, 380.00, 25_000_000, 2_500_000_000_000, 0.35, 36.4, 12.5, 48.7, "Technology"),
            ("JNJ", 60.0, 155.20, 8_000_000, 380_000_000_000, 0.52, 18.1, 3.2, 42.1, "Healthcare"),
            ("KO", 45.0, 58.30, 12_000_000, 250_000_000_000, 1.80, 21.5, 5.0, 61.3, "Consumer Staples"),
        ]:
            s = _make_stock(
                sym, _all_pass_filters(), score=score, price=price,
                avg_volume=vol, market_cap=mcap, debt_equity=de,
                net_margin=margin, sales_growth=growth, rsi_14=rsi, sector=sector,
            )
            stocks.append(s)
        return stocks

    def test_table_has_column_headers(self):
        console = _capture_console()
        stocks = self._make_passing_stocks()
        render_results_table(stocks, console=console)
        output = console.file.getvalue()
        for col in ["Symbol", "Price", "AvgVol", "MktCap", "D/E", "Margin", "Growth", "RSI", "Score", "Sector"]:
            assert col in output, f"Column '{col}' not found in table output"

    def test_table_row_count(self):
        console = _capture_console()
        stocks = self._make_passing_stocks()
        render_results_table(stocks, console=console)
        output = console.file.getvalue()
        # All 4 passing stocks should appear; check symbols
        for sym in ["AAPL", "MSFT", "JNJ", "KO"]:
            assert sym in output

    def test_sorted_by_score_descending(self):
        console = _capture_console()
        stocks = self._make_passing_stocks()
        render_results_table(stocks, console=console)
        output = console.file.getvalue()
        # AAPL (85) should appear before KO (45) in output
        assert output.index("AAPL") < output.index("KO")

    def test_score_colors_in_markup(self):
        console = Console(file=StringIO(), width=120, highlight=False, markup=True)
        stocks = self._make_passing_stocks()
        render_results_table(stocks, console=console)
        output = console.file.getvalue()
        # Scores should be styled -- check for the score values in the output
        assert "85.0" in output or "85.00" in output

    def test_zero_passing_stocks(self):
        console = _capture_console()
        # All stocks fail filters
        s = _make_stock("FAIL", [FilterResult("bar_data", False, reason="no data")], score=None)
        render_results_table([s], console=console)
        output = console.file.getvalue()
        assert "No stocks passed all filters" in output

    def test_empty_list(self):
        console = _capture_console()
        render_results_table([], console=console)
        output = console.file.getvalue()
        assert "No stocks passed all filters" in output

    def test_only_passing_scored_stocks_shown(self):
        console = _capture_console()
        passing = _make_stock("GOOD", _all_pass_filters(), score=75.0, price=100.0, sector="Tech")
        failing = _make_stock("BAD", [FilterResult("bar_data", False)], score=None)
        no_score = _make_stock("NOSCORE", _all_pass_filters(), score=None)
        render_results_table([passing, failing, no_score], console=console)
        output = console.file.getvalue()
        assert "GOOD" in output
        assert "BAD" not in output
        assert "NOSCORE" not in output


# ===========================================================================
# Stage summary panel
# ===========================================================================


class TestRenderStageSummary:
    """Test render_stage_summary output."""

    def _build_mixed_stocks(self) -> list[ScreenedStock]:
        """Build ~10 stocks with varied filter outcomes.

        - 2 fail bar_data (no further filters)
        - 2 fail stage 1 (price_range, avg_volume)
        - 3 fail stage 2 (market_cap, sector, optionable)
        - 3 pass all filters with scores
        """
        stocks = []

        # 2 fail bar_data
        for sym in ["NOBAR1", "NOBAR2"]:
            stocks.append(_make_stock(sym, [FilterResult("bar_data", False, reason="no data")]))

        # 2 fail stage 1 filters (pass bar_data, fail price_range or avg_volume)
        for sym, fail_filter in [("LOWPRC", "price_range"), ("LOWVOL", "avg_volume")]:
            results = [FilterResult("bar_data", True)]
            s1_names = ["price_range", "avg_volume", "rsi", "sma200"]
            for fn in s1_names:
                results.append(FilterResult(fn, fn != fail_filter))
            stocks.append(_make_stock(sym, results))

        # 3 fail stage 2 filters (pass bar_data + stage 1, fail one stage 2)
        s1_pass = [FilterResult("bar_data", True)]
        for fn in ["price_range", "avg_volume", "rsi", "sma200"]:
            s1_pass.append(FilterResult(fn, True))

        for sym, fail_filter in [("SMALLCAP", "market_cap"), ("BADSEC", "sector"), ("NOOPT", "optionable")]:
            results = list(s1_pass)  # copy
            s2_names = ["market_cap", "debt_equity", "net_margin", "sales_growth", "sector", "optionable"]
            for fn in s2_names:
                results.append(FilterResult(fn, fn != fail_filter))
            stocks.append(_make_stock(sym, results))

        # 3 pass everything with scores
        for sym, score in [("GOOD1", 80.0), ("GOOD2", 65.0), ("GOOD3", 50.0)]:
            stocks.append(_make_stock(sym, _all_pass_filters(), score=score))

        return stocks

    def test_panel_title(self):
        console = _capture_console()
        stocks = self._build_mixed_stocks()
        render_stage_summary(stocks, console=console)
        output = console.file.getvalue()
        assert "Filter Summary" in output

    def test_universe_count(self):
        console = _capture_console()
        stocks = self._build_mixed_stocks()
        render_stage_summary(stocks, console=console)
        output = console.file.getvalue()
        assert "10" in output  # 10 total stocks

    def test_stage_counts(self):
        console = _capture_console()
        stocks = self._build_mixed_stocks()
        render_stage_summary(stocks, console=console)
        output = console.file.getvalue()
        # After bars: 10 - 2 = 8
        assert "8" in output
        # Stage 1: 8 - 2 = 6
        assert "6" in output
        # Stage 2: 6 - 3 = 3
        assert "3" in output

    def test_empty_stock_list(self):
        console = _capture_console()
        render_stage_summary([], console=console)
        output = console.file.getvalue()
        assert "Filter Summary" in output
        assert "0" in output

    def test_reduction_counts_shown(self):
        console = _capture_console()
        stocks = self._build_mixed_stocks()
        render_stage_summary(stocks, console=console)
        output = console.file.getvalue()
        # Reductions should appear as (-N) in output
        assert "(-2)" in output  # bar_data removes 2


# ===========================================================================
# Filter breakdown table
# ===========================================================================


class TestRenderFilterBreakdown:
    """Test render_filter_breakdown output."""

    def _build_mixed_stocks(self) -> list[ScreenedStock]:
        """Same as TestRenderStageSummary."""
        stocks = []

        for sym in ["NOBAR1", "NOBAR2"]:
            stocks.append(_make_stock(sym, [FilterResult("bar_data", False, reason="no data")]))

        for sym, fail_filter in [("LOWPRC", "price_range"), ("LOWVOL", "avg_volume")]:
            results = [FilterResult("bar_data", True)]
            for fn in ["price_range", "avg_volume", "rsi", "sma200"]:
                results.append(FilterResult(fn, fn != fail_filter))
            stocks.append(_make_stock(sym, results))

        s1_pass = [FilterResult("bar_data", True)]
        for fn in ["price_range", "avg_volume", "rsi", "sma200"]:
            s1_pass.append(FilterResult(fn, True))

        for sym, fail_filter in [("SMALLCAP", "market_cap"), ("BADSEC", "sector"), ("NOOPT", "optionable")]:
            results = list(s1_pass)
            for fn in ["market_cap", "debt_equity", "net_margin", "sales_growth", "sector", "optionable"]:
                results.append(FilterResult(fn, fn != fail_filter))
            stocks.append(_make_stock(sym, results))

        for sym, score in [("GOOD1", 80.0), ("GOOD2", 65.0), ("GOOD3", 50.0)]:
            stocks.append(_make_stock(sym, _all_pass_filters(), score=score))

        return stocks

    def test_breakdown_title(self):
        console = _capture_console()
        stocks = self._build_mixed_stocks()
        render_filter_breakdown(stocks, console=console)
        output = console.file.getvalue()
        assert "Filter Breakdown" in output

    def test_active_filters_appear(self):
        console = _capture_console()
        stocks = self._build_mixed_stocks()
        render_filter_breakdown(stocks, console=console)
        output = console.file.getvalue()
        # Filters that removed stocks should appear
        assert "bar_data" in output
        assert "price_range" in output
        assert "avg_volume" in output
        assert "market_cap" in output
        assert "sector" in output
        assert "optionable" in output

    def test_inactive_filters_hidden(self):
        console = _capture_console()
        stocks = self._build_mixed_stocks()
        render_filter_breakdown(stocks, console=console)
        output = console.file.getvalue()
        # Filters that removed 0 stocks should NOT appear
        assert "debt_equity" not in output
        assert "net_margin" not in output
        assert "sales_growth" not in output
        # rsi and sma200 removed 0 stocks too
        assert "sma200" not in output

    def test_remaining_is_waterfall(self):
        console = _capture_console()
        stocks = self._build_mixed_stocks()
        render_filter_breakdown(stocks, console=console)
        output = console.file.getvalue()
        # bar_data removes 2 -> remaining 8
        assert "8" in output
        # After all removals, final remaining should be 3
        assert "3" in output

    def test_all_passing_minimal_output(self):
        console = _capture_console()
        stocks = [_make_stock("A", _all_pass_filters(), score=90.0)]
        render_filter_breakdown(stocks, console=console)
        output = console.file.getvalue()
        assert "Filter Breakdown" in output
        # No filter names should appear since nothing was removed
        assert "bar_data" not in output


# ===========================================================================
# Progress callback
# ===========================================================================


class TestProgressCallback:
    """Test progress_context callback factory."""

    def test_progress_context_yields_callable(self):
        from screener.display import progress_context

        console = Console(file=StringIO(), width=120)
        with progress_context(console=console) as callback:
            assert callable(callback)

    def test_callback_creates_and_updates_tasks(self):
        from screener.display import progress_context

        console = Console(file=StringIO(), width=120)
        with progress_context(console=console) as callback:
            callback("Fetching Alpaca bars", 1, 10)
            callback("Fetching Alpaca bars", 5, 10)
            callback("Fetching Alpaca bars", 10, 10)
        # No exceptions means success

    def test_callback_with_symbol(self):
        from screener.display import progress_context

        console = Console(file=StringIO(), width=120)
        with progress_context(console=console) as callback:
            callback("Fetching Finnhub data", 1, 5, symbol="AAPL")
            callback("Fetching Finnhub data", 2, 5, symbol="MSFT")
        # No exceptions means success

    def test_callback_multiple_stages(self):
        from screener.display import progress_context

        console = Console(file=StringIO(), width=120)
        with progress_context(console=console) as callback:
            callback("Fetching Alpaca bars", 100, 100)
            callback("Filtering Stage 1", 1, 100)
            callback("Filtering Stage 1", 50, 100)
            callback("Filtering Stage 1", 100, 100)
            callback("Fetching Finnhub data", 1, 50, symbol="AAPL")
            callback("Scoring", 50, 50)
        # No exceptions means success
