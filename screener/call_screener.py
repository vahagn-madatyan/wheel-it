"""Covered call screening: fetch, filter, rank, and display call recommendations.

Given a symbol and cost basis, fetches OTM call contracts from Alpaca, applies
DTE/OI/spread/delta filters (reusing put screener preset thresholds), enforces
strike >= cost basis, and ranks by annualized return.

Used standalone via `run-call-screener` CLI and integrated into `run-strategy`
for automatic covered call selection on assigned positions.
"""

import logging as stdlib_logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from rich.box import ROUNDED
from rich.console import Console
from rich.table import Table

from alpaca.data.requests import OptionSnapshotRequest
from alpaca.trading.enums import AssetStatus, ContractType
from alpaca.trading.requests import GetOptionContractsRequest

from config.params import DELTA_MIN, DELTA_MAX
from screener.config_loader import ScreenerConfig

logger = stdlib_logging.getLogger(__name__)

_default_console = Console()

# DTE range for call screening — same as put screener pipeline (D032)
_CALL_DTE_MIN = 14
_CALL_DTE_MAX = 60


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class CallRecommendation:
    """A scored covered call recommendation."""

    symbol: str  # option contract symbol
    underlying: str  # underlying stock symbol
    strike: float
    dte: int
    premium: float  # bid price (what seller receives)
    delta: Optional[float]
    oi: int
    spread: float  # bid/ask spread as fraction
    annualized_return: float  # annualized return percentage
    cost_basis: float  # input cost basis for context


# ---------------------------------------------------------------------------
# Annualized return computation
# ---------------------------------------------------------------------------


def compute_call_annualized_return(
    premium: float,
    cost_basis: float,
    dte: int,
) -> Optional[float]:
    """Compute annualized return from selling a covered call.

    Formula: (premium / cost_basis) * (365 / dte) * 100

    Args:
        premium: Bid price of the call option.
        cost_basis: Average entry price of the underlying shares.
        dte: Days to expiration.

    Returns:
        Annualized return as a percentage (e.g. 24.3 for 24.3%), or None
        if inputs are invalid (zero cost basis, zero DTE, negative premium).
    """
    if cost_basis <= 0 or dte <= 0 or premium < 0:
        return None
    return round((premium / cost_basis) * (365 / dte) * 100, 2)


# ---------------------------------------------------------------------------
# Core screening logic
# ---------------------------------------------------------------------------


def screen_calls(
    trade_client,
    option_client,
    symbol: str,
    cost_basis: float,
    config: Optional[ScreenerConfig] = None,
) -> list[CallRecommendation]:
    """Screen and rank covered call opportunities for a symbol.

    Steps:
    1. Fetch active call contracts in the DTE range (14–60 days).
    2. Filter to strikes >= cost basis (never sell below cost basis).
    3. Batch-fetch snapshots for bid/ask/delta data.
    4. Apply OI, spread, and delta filters from screener config/presets.
    5. Compute annualized return for each passing contract.
    6. Sort by annualized return descending.

    Args:
        trade_client: Alpaca TradingClient for contract discovery.
        option_client: Alpaca OptionHistoricalDataClient for snapshots.
        symbol: Underlying stock ticker (e.g. "AAPL").
        cost_basis: Average entry price of shares (strike >= this).
        config: ScreenerConfig for OI/spread thresholds. Uses defaults
            if None.

    Returns:
        List of CallRecommendation sorted by annualized return descending.
        Empty list if no contracts pass all filters.
    """
    if config is None:
        config = ScreenerConfig()

    oi_min = config.options.options_oi_min
    spread_max = config.options.options_spread_max

    today = date.today()
    min_exp = today + timedelta(days=_CALL_DTE_MIN)
    max_exp = today + timedelta(days=_CALL_DTE_MAX)

    # Step 1: Fetch call contracts
    try:
        req = GetOptionContractsRequest(
            underlying_symbols=[symbol],
            type=ContractType.CALL,
            status=AssetStatus.ACTIVE,
            expiration_date_gte=min_exp,
            expiration_date_lte=max_exp,
            limit=1000,
        )
        response = trade_client.get_option_contracts(req)
        contracts = response.option_contracts if response.option_contracts else []
    except Exception:
        logger.debug("Failed to fetch call contracts for %s", symbol)
        return []

    if not contracts:
        logger.debug("No call contracts found for %s in DTE range %d–%d", symbol, _CALL_DTE_MIN, _CALL_DTE_MAX)
        return []

    # Step 2: Filter to strikes >= cost basis
    eligible = [c for c in contracts if float(c.strike_price) >= cost_basis]
    if not eligible:
        logger.debug("No call contracts for %s with strike >= cost basis $%.2f", symbol, cost_basis)
        return []

    # Step 3: Pre-filter by OI from contract data
    oi_passing = []
    for c in eligible:
        oi = int(c.open_interest) if c.open_interest is not None else 0
        if oi >= oi_min:
            oi_passing.append(c)

    if not oi_passing:
        logger.debug("No call contracts for %s with OI >= %d", symbol, oi_min)
        return []

    # Step 4: Batch-fetch snapshots
    contract_symbols = [c.symbol for c in oi_passing]
    try:
        all_snapshots = {}
        for i in range(0, len(contract_symbols), 100):
            batch = contract_symbols[i : i + 100]
            snap_req = OptionSnapshotRequest(symbol_or_symbols=batch)
            result = option_client.get_option_snapshot(snap_req)
            all_snapshots.update(result)
    except Exception:
        logger.debug("Failed to fetch snapshots for %s call contracts", symbol)
        return []

    # Step 5: Apply spread and delta filters, compute return
    recommendations: list[CallRecommendation] = []

    for contract in oi_passing:
        snap = all_snapshots.get(contract.symbol)
        if snap is None:
            continue

        # Extract bid/ask
        bid = None
        ask = None
        if hasattr(snap, "latest_quote") and snap.latest_quote:
            bid = float(snap.latest_quote.bid_price)
            ask = float(snap.latest_quote.ask_price)

        if bid is None or ask is None or bid <= 0:
            continue

        # Compute spread
        midpoint = (bid + ask) / 2
        if midpoint <= 0:
            continue
        spread = (ask - bid) / midpoint

        # Spread filter
        if spread > spread_max:
            continue

        # Delta filter (calls have positive delta)
        delta = None
        if hasattr(snap, "greeks") and snap.greeks:
            delta = snap.greeks.delta

        if delta is not None:
            abs_delta = abs(delta)
            if abs_delta < DELTA_MIN or abs_delta > DELTA_MAX:
                continue

        oi = int(contract.open_interest) if contract.open_interest is not None else 0
        dte = (contract.expiration_date - today).days
        strike = float(contract.strike_price)

        ann_return = compute_call_annualized_return(bid, cost_basis, dte)
        if ann_return is None:
            continue

        recommendations.append(
            CallRecommendation(
                symbol=contract.symbol,
                underlying=symbol,
                strike=strike,
                dte=dte,
                premium=bid,
                delta=delta,
                oi=oi,
                spread=spread,
                annualized_return=ann_return,
                cost_basis=cost_basis,
            )
        )

    # Step 6: Sort by annualized return descending
    recommendations.sort(key=lambda r: r.annualized_return, reverse=True)

    logger.info(
        "Call screener for %s: %d contracts fetched, %d recommendations",
        symbol,
        len(contracts),
        len(recommendations),
    )

    return recommendations


# ---------------------------------------------------------------------------
# Rich table display
# ---------------------------------------------------------------------------


def render_call_results_table(
    recommendations: list[CallRecommendation],
    symbol: str,
    cost_basis: float,
    console: Optional[Console] = None,
) -> None:
    """Render a Rich table of covered call recommendations.

    Args:
        recommendations: Sorted list of CallRecommendation objects.
        symbol: Underlying stock symbol.
        cost_basis: Input cost basis for header display.
        console: Optional Rich Console for output.
    """
    console = console or _default_console

    if not recommendations:
        console.print(
            f"[yellow]No covered call recommendations for {symbol} "
            f"(cost basis ${cost_basis:.2f}).[/yellow]"
        )
        return

    table = Table(
        title=f"Covered Call Recommendations — {symbol} (Cost Basis: ${cost_basis:.2f})",
        box=ROUNDED,
        header_style="bold cyan",
        row_styles=["", "dim"],
    )

    table.add_column("#", justify="right", style="dim", width=4, no_wrap=True)
    table.add_column("Symbol", style="bold", no_wrap=True)
    table.add_column("Strike", justify="right")
    table.add_column("DTE", justify="right")
    table.add_column("Premium", justify="right")
    table.add_column("Delta", justify="right")
    table.add_column("OI", justify="right")
    table.add_column("Spread", justify="right")
    table.add_column("Ann. Return", justify="right")

    for idx, rec in enumerate(recommendations, start=1):
        delta_str = f"{rec.delta:.3f}" if rec.delta is not None else "N/A"
        spread_str = f"{rec.spread:.1%}"
        return_str = f"[green]{rec.annualized_return:.1f}%[/green]"

        table.add_row(
            str(idx),
            rec.symbol,
            f"${rec.strike:.2f}",
            str(rec.dte),
            f"${rec.premium:.2f}",
            delta_str,
            f"{rec.oi:,}",
            spread_str,
            return_str,
        )

    console.print(table)
