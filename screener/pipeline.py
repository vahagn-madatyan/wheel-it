"""Screening pipeline filter functions and stage runners.

Each filter function takes a ScreenedStock and ScreenerConfig, returns a FilterResult.
Filters never raise — they return passed=False with a descriptive reason on failure
or missing data.

Stage 1 filters are cheap (Alpaca-based): price, volume, RSI, SMA200.
Stage 2 filters are expensive (Finnhub-based): market cap, D/E, margin, growth, sector, optionable.
"""

import logging as stdlib_logging

import numpy as np
import pandas as pd

from models.screened_stock import FilterResult, ScreenedStock
from screener.config_loader import ScreenerConfig
from screener.finnhub_client import FinnhubClient, extract_metric

logger = stdlib_logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stage 1 filters (cheap, Alpaca-based)
# ---------------------------------------------------------------------------


def filter_price_range(stock: ScreenedStock, config: ScreenerConfig) -> FilterResult:
    """Check if stock price is within [price_min, price_max].

    Args:
        stock: ScreenedStock with price field populated.
        config: ScreenerConfig with technicals.price_min and price_max.

    Returns:
        FilterResult with pass/fail and reason.
    """
    price_min = config.technicals.price_min
    price_max = config.technicals.price_max

    if stock.price is None:
        return FilterResult(
            filter_name="price_range",
            passed=False,
            actual_value=None,
            threshold=None,
            reason="Price data unavailable",
        )

    if stock.price < price_min:
        return FilterResult(
            filter_name="price_range",
            passed=False,
            actual_value=stock.price,
            threshold=price_min,
            reason=f"Price ${stock.price:.2f} below minimum ${price_min:.2f}",
        )

    if stock.price > price_max:
        return FilterResult(
            filter_name="price_range",
            passed=False,
            actual_value=stock.price,
            threshold=price_max,
            reason=f"Price ${stock.price:.2f} above maximum ${price_max:.2f}",
        )

    return FilterResult(
        filter_name="price_range",
        passed=True,
        actual_value=stock.price,
        threshold=None,
        reason="",
    )


def filter_avg_volume(stock: ScreenedStock, config: ScreenerConfig) -> FilterResult:
    """Check if average volume meets minimum threshold.

    Args:
        stock: ScreenedStock with avg_volume field populated.
        config: ScreenerConfig with technicals.avg_volume_min.

    Returns:
        FilterResult with pass/fail and reason.
    """
    min_volume = config.technicals.avg_volume_min

    if stock.avg_volume is None:
        return FilterResult(
            filter_name="avg_volume",
            passed=False,
            actual_value=None,
            threshold=min_volume,
            reason="Volume data unavailable",
        )

    if stock.avg_volume < min_volume:
        return FilterResult(
            filter_name="avg_volume",
            passed=False,
            actual_value=stock.avg_volume,
            threshold=min_volume,
            reason=f"Avg volume {stock.avg_volume:,.0f} below minimum {min_volume:,}",
        )

    return FilterResult(
        filter_name="avg_volume",
        passed=True,
        actual_value=stock.avg_volume,
        threshold=min_volume,
        reason="",
    )


def filter_rsi(stock: ScreenedStock, config: ScreenerConfig) -> FilterResult:
    """Check if RSI(14) is at or below maximum threshold.

    Args:
        stock: ScreenedStock with rsi_14 field populated.
        config: ScreenerConfig with technicals.rsi_max.

    Returns:
        FilterResult with pass/fail and reason.
    """
    rsi_max = config.technicals.rsi_max

    if stock.rsi_14 is None:
        return FilterResult(
            filter_name="rsi",
            passed=False,
            actual_value=None,
            threshold=rsi_max,
            reason="RSI data unavailable",
        )

    if stock.rsi_14 > rsi_max:
        return FilterResult(
            filter_name="rsi",
            passed=False,
            actual_value=stock.rsi_14,
            threshold=rsi_max,
            reason=f"RSI {stock.rsi_14:.1f} above maximum {rsi_max:.1f}",
        )

    return FilterResult(
        filter_name="rsi",
        passed=True,
        actual_value=stock.rsi_14,
        threshold=rsi_max,
        reason="",
    )


def filter_sma200(stock: ScreenedStock, config: ScreenerConfig) -> FilterResult:
    """Check if stock is above its 200-day SMA.

    If config.technicals.above_sma200 is False, the filter is disabled and
    always passes.

    Args:
        stock: ScreenedStock with above_sma200 field populated.
        config: ScreenerConfig with technicals.above_sma200.

    Returns:
        FilterResult with pass/fail and reason.
    """
    if not config.technicals.above_sma200:
        return FilterResult(
            filter_name="sma200",
            passed=True,
            actual_value=None,
            threshold=None,
            reason="",
        )

    if stock.above_sma200 is None:
        return FilterResult(
            filter_name="sma200",
            passed=False,
            actual_value=None,
            threshold=None,
            reason="SMA(200) data unavailable",
        )

    if not stock.above_sma200:
        return FilterResult(
            filter_name="sma200",
            passed=False,
            actual_value=0.0,
            threshold=1.0,
            reason="Price is below SMA(200)",
        )

    return FilterResult(
        filter_name="sma200",
        passed=True,
        actual_value=1.0,
        threshold=1.0,
        reason="",
    )


# ---------------------------------------------------------------------------
# Stage 2 filters (expensive, Finnhub-based)
# ---------------------------------------------------------------------------


def filter_market_cap(stock: ScreenedStock, config: ScreenerConfig) -> FilterResult:
    """Check if market cap meets minimum threshold.

    stock.market_cap is expected to be in raw dollars (already converted
    from Finnhub's millions format by the pipeline orchestration).

    Args:
        stock: ScreenedStock with market_cap field populated (in dollars).
        config: ScreenerConfig with fundamentals.market_cap_min (in dollars).

    Returns:
        FilterResult with pass/fail and reason.
    """
    min_cap = config.fundamentals.market_cap_min

    if stock.market_cap is None:
        return FilterResult(
            filter_name="market_cap",
            passed=False,
            actual_value=None,
            threshold=min_cap,
            reason="Market cap data unavailable",
        )

    if stock.market_cap < min_cap:
        return FilterResult(
            filter_name="market_cap",
            passed=False,
            actual_value=stock.market_cap,
            threshold=min_cap,
            reason=f"Market cap ${stock.market_cap:,.0f} below minimum ${min_cap:,}",
        )

    return FilterResult(
        filter_name="market_cap",
        passed=True,
        actual_value=stock.market_cap,
        threshold=min_cap,
        reason="",
    )


def filter_debt_equity(stock: ScreenedStock, config: ScreenerConfig) -> FilterResult:
    """Check if debt-to-equity ratio is at or below maximum threshold.

    Args:
        stock: ScreenedStock with debt_equity field populated.
        config: ScreenerConfig with fundamentals.debt_equity_max.

    Returns:
        FilterResult with pass/fail and reason.
    """
    max_de = config.fundamentals.debt_equity_max

    if stock.debt_equity is None:
        return FilterResult(
            filter_name="debt_equity",
            passed=False,
            actual_value=None,
            threshold=max_de,
            reason="Debt/equity data unavailable",
        )

    if stock.debt_equity > max_de:
        return FilterResult(
            filter_name="debt_equity",
            passed=False,
            actual_value=stock.debt_equity,
            threshold=max_de,
            reason=f"D/E ratio {stock.debt_equity:.2f} above maximum {max_de:.2f}",
        )

    return FilterResult(
        filter_name="debt_equity",
        passed=True,
        actual_value=stock.debt_equity,
        threshold=max_de,
        reason="",
    )


def filter_net_margin(stock: ScreenedStock, config: ScreenerConfig) -> FilterResult:
    """Check if net margin meets minimum threshold.

    Args:
        stock: ScreenedStock with net_margin field populated.
        config: ScreenerConfig with fundamentals.net_margin_min.

    Returns:
        FilterResult with pass/fail and reason.
    """
    min_margin = config.fundamentals.net_margin_min

    if stock.net_margin is None:
        return FilterResult(
            filter_name="net_margin",
            passed=False,
            actual_value=None,
            threshold=min_margin,
            reason="Net margin data unavailable",
        )

    if stock.net_margin < min_margin:
        return FilterResult(
            filter_name="net_margin",
            passed=False,
            actual_value=stock.net_margin,
            threshold=min_margin,
            reason=f"Net margin {stock.net_margin:.1f}% below minimum {min_margin:.1f}%",
        )

    return FilterResult(
        filter_name="net_margin",
        passed=True,
        actual_value=stock.net_margin,
        threshold=min_margin,
        reason="",
    )


def filter_sales_growth(stock: ScreenedStock, config: ScreenerConfig) -> FilterResult:
    """Check if sales growth meets minimum threshold.

    Args:
        stock: ScreenedStock with sales_growth field populated.
        config: ScreenerConfig with fundamentals.sales_growth_min.

    Returns:
        FilterResult with pass/fail and reason.
    """
    min_growth = config.fundamentals.sales_growth_min

    if stock.sales_growth is None:
        return FilterResult(
            filter_name="sales_growth",
            passed=False,
            actual_value=None,
            threshold=min_growth,
            reason="Sales growth data unavailable",
        )

    if stock.sales_growth < min_growth:
        return FilterResult(
            filter_name="sales_growth",
            passed=False,
            actual_value=stock.sales_growth,
            threshold=min_growth,
            reason=f"Sales growth {stock.sales_growth:.1f}% below minimum {min_growth:.1f}%",
        )

    return FilterResult(
        filter_name="sales_growth",
        passed=True,
        actual_value=stock.sales_growth,
        threshold=min_growth,
        reason="",
    )


def filter_sector(stock: ScreenedStock, config: ScreenerConfig) -> FilterResult:
    """Check if stock sector passes inclusion/exclusion filters.

    Logic:
    - If sector is None, fail with "Sector data unavailable".
    - If include list is non-empty, sector must be in it (case-insensitive).
    - If sector is in exclude list (case-insensitive), fail.
    - Otherwise, pass.

    Args:
        stock: ScreenedStock with sector field populated.
        config: ScreenerConfig with sectors.include and sectors.exclude.

    Returns:
        FilterResult with pass/fail and reason.
    """
    if stock.sector is None:
        return FilterResult(
            filter_name="sector",
            passed=False,
            actual_value=None,
            threshold=None,
            reason="Sector data unavailable",
        )

    sector_lower = stock.sector.lower()
    include_lower = [s.lower() for s in config.sectors.include]
    exclude_lower = [s.lower() for s in config.sectors.exclude]

    if include_lower and sector_lower not in include_lower:
        return FilterResult(
            filter_name="sector",
            passed=False,
            actual_value=None,
            threshold=None,
            reason=f"Sector '{stock.sector}' not in include list",
        )

    if sector_lower in exclude_lower:
        return FilterResult(
            filter_name="sector",
            passed=False,
            actual_value=None,
            threshold=None,
            reason=f"Sector '{stock.sector}' is in exclude list",
        )

    return FilterResult(
        filter_name="sector",
        passed=True,
        actual_value=None,
        threshold=None,
        reason="",
    )


def filter_optionable(
    stock: ScreenedStock,
    config: ScreenerConfig,
    optionable_set: set[str],
) -> FilterResult:
    """Check if stock symbol is in the set of optionable symbols.

    If config.options.optionable is False, the filter is disabled and
    always passes.

    Args:
        stock: ScreenedStock with symbol field.
        config: ScreenerConfig with options.optionable.
        optionable_set: Set of ticker symbols that have options available.

    Returns:
        FilterResult with pass/fail and reason.
    """
    if not config.options.optionable:
        return FilterResult(
            filter_name="optionable",
            passed=True,
            actual_value=None,
            threshold=None,
            reason="",
        )

    if stock.symbol not in optionable_set:
        return FilterResult(
            filter_name="optionable",
            passed=False,
            actual_value=None,
            threshold=None,
            reason=f"{stock.symbol} is not optionable",
        )

    return FilterResult(
        filter_name="optionable",
        passed=True,
        actual_value=None,
        threshold=None,
        reason="",
    )


# ---------------------------------------------------------------------------
# Historical volatility computation
# ---------------------------------------------------------------------------


def compute_historical_volatility(
    bars_df: pd.DataFrame,
    window: int = 30,
) -> float | None:
    """Compute annualized historical volatility from daily close prices.

    Uses log returns of close prices, calculates the standard deviation of
    the last `window` returns, and annualizes with sqrt(252).

    Args:
        bars_df: DataFrame with a 'close' column of daily close prices.
        window: Number of trading days for the rolling window (default 30).

    Returns:
        Annualized historical volatility as a float, or None if fewer than
        window+1 data points (need window+1 prices to get window returns).
    """
    if len(bars_df) < window + 1:
        return None

    close = bars_df["close"].values
    log_returns = np.log(close[1:] / close[:-1])

    # Use the last `window` returns
    recent_returns = log_returns[-window:]
    daily_std = np.std(recent_returns, ddof=1)

    annualized_hv = daily_std * np.sqrt(252)
    return float(annualized_hv)


# ---------------------------------------------------------------------------
# Stage runner helpers
# ---------------------------------------------------------------------------


def run_stage_1_filters(stock: ScreenedStock, config: ScreenerConfig) -> bool:
    """Run all 4 Stage 1 (cheap) filters and record results.

    Runs all filters regardless of individual outcomes. Appends each
    FilterResult to stock.filter_results.

    Args:
        stock: ScreenedStock with Alpaca-based fields populated.
        config: ScreenerConfig with technicals thresholds.

    Returns:
        True only if all 4 filters passed.
    """
    results = [
        filter_price_range(stock, config),
        filter_avg_volume(stock, config),
        filter_rsi(stock, config),
        filter_sma200(stock, config),
    ]

    for r in results:
        stock.filter_results.append(r)

    return all(r.passed for r in results)


def run_stage_2_filters(
    stock: ScreenedStock,
    config: ScreenerConfig,
    finnhub_client: FinnhubClient,
    optionable_set: set[str],
) -> bool:
    """Run all 6 Stage 2 (expensive) filters with Finnhub data.

    Fetches company profile and metrics from Finnhub, populates stock fields,
    then runs all 6 Stage 2 filters.

    If the Finnhub profile is an empty dict (symbol not found), fails all
    Finnhub-dependent filters with reason "No Finnhub data available".

    Args:
        stock: ScreenedStock to populate and filter.
        config: ScreenerConfig with fundamental/sector/options thresholds.
        finnhub_client: FinnhubClient instance for API calls.
        optionable_set: Set of optionable ticker symbols.

    Returns:
        True only if all 6 filters passed.
    """
    profile = finnhub_client.company_profile(stock.symbol)
    metrics_response = finnhub_client.company_metrics(stock.symbol)
    metrics = metrics_response.get("metric", {})

    if not profile:
        # No Finnhub data — fail all Finnhub-dependent filters
        no_data_reason = "No Finnhub data available"
        results = [
            FilterResult(filter_name="market_cap", passed=False, reason=no_data_reason),
            FilterResult(filter_name="debt_equity", passed=False, reason=no_data_reason),
            FilterResult(filter_name="net_margin", passed=False, reason=no_data_reason),
            FilterResult(filter_name="sales_growth", passed=False, reason=no_data_reason),
            FilterResult(filter_name="sector", passed=False, reason=no_data_reason),
            filter_optionable(stock, config, optionable_set),
        ]
        for r in results:
            stock.filter_results.append(r)
        return all(r.passed for r in results)

    # Populate stock fields from Finnhub data
    raw_market_cap = profile.get("marketCapitalization")
    stock.market_cap = (
        raw_market_cap * 1_000_000 if raw_market_cap is not None else None
    )
    stock.sector = profile.get("finnhubIndustry")
    stock.debt_equity = extract_metric(metrics, "debt_equity")
    stock.net_margin = extract_metric(metrics, "net_margin")
    stock.sales_growth = extract_metric(metrics, "sales_growth")

    # Run all 6 Stage 2 filters
    results = [
        filter_market_cap(stock, config),
        filter_debt_equity(stock, config),
        filter_net_margin(stock, config),
        filter_sales_growth(stock, config),
        filter_sector(stock, config),
        filter_optionable(stock, config, optionable_set),
    ]

    for r in results:
        stock.filter_results.append(r)

    return all(r.passed for r in results)
