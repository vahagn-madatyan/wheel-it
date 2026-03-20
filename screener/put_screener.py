"""Cash-secured put screening: fetch, filter, rank, and display put recommendations.

Given a list of symbols and buying power, fetches OTM put contracts from Alpaca,
pre-filters by buying power affordability, applies DTE/OI/spread/delta filters
(reusing screener preset thresholds), enforces one-per-underlying diversification,
and ranks by annualized return.

Used standalone via `run-put-screener` CLI and integrated into `run-strategy`
for automatic put selection when selling cash-secured puts.
"""

import logging as stdlib_logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from rich.box import ROUNDED
from rich.console import Console
from rich.table import Table

from alpaca.data.requests import OptionSnapshotRequest
from alpaca.data.historical.stock import StockLatestTradeRequest
from alpaca.trading.enums import AssetStatus, ContractType
from alpaca.trading.requests import GetOptionContractsRequest

from config.params import DELTA_MIN, DELTA_MAX
from screener.config_loader import ScreenerConfig

logger = stdlib_logging.getLogger(__name__)

_default_console = Console()



# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class PutRecommendation:
    """A scored cash-secured put recommendation."""

    symbol: str  # option contract symbol
    underlying: str  # underlying stock symbol
    strike: float
    dte: int
    premium: float  # bid price (what seller receives)
    extrinsic: float  # time value portion of premium
    delta: Optional[float]
    oi: int
    spread: float  # bid/ask spread as fraction
    annualized_return: float  # annualized return based on extrinsic premium


# ---------------------------------------------------------------------------
# Annualized return computation
# ---------------------------------------------------------------------------


def compute_put_annualized_return(
    premium: float,
    strike: float,
    dte: int,
) -> Optional[float]:
    """Compute annualized return from selling a cash-secured put.

    Formula: (premium / strike) * (365 / dte) * 100

    The denominator is strike (not cost basis) because the capital at risk
    for a cash-secured put is strike × 100 (D046).

    Args:
        premium: Bid price of the put option.
        strike: Strike price of the put option.
        dte: Days to expiration.

    Returns:
        Annualized return as a percentage (e.g. 12.17 for 12.17%), or None
        if inputs are invalid (zero strike, zero DTE, negative premium).
    """
    if strike <= 0 or dte <= 0 or premium < 0:
        return None
    return round((premium / strike) * (365 / dte) * 100, 2)


# ---------------------------------------------------------------------------
# Core screening logic
# ---------------------------------------------------------------------------


def screen_puts(
    trade_client,
    option_client,
    symbols: list[str],
    buying_power: float,
    config: Optional[ScreenerConfig] = None,
    stock_client=None,
) -> list[PutRecommendation]:
    """Screen and rank cash-secured put opportunities across multiple symbols.

    Steps:
    1. Pre-filter symbols by buying power affordability.
    2. Fetch active put contracts in the DTE range (14–60 days) with pagination.
    3. Pre-filter by OI from contract data.
    4. Batch-fetch snapshots for bid/ask/delta data.
    5. Apply spread and delta filters.
    6. Compute annualized return for each passing contract.
    7. Select one-per-underlying (best annualized return per symbol).
    8. Sort by annualized return descending.

    Args:
        trade_client: Alpaca TradingClient for contract discovery.
        option_client: Alpaca OptionHistoricalDataClient for snapshots.
        symbols: List of underlying stock tickers to screen.
        buying_power: Maximum cash available for securing puts.
        config: ScreenerConfig for OI/spread thresholds. Uses defaults if None.
        stock_client: Alpaca StockHistoricalDataClient for latest trade prices.
            If None, buying power pre-filter is skipped (all symbols proceed).

    Returns:
        List of PutRecommendation sorted by annualized return descending,
        with at most one recommendation per underlying symbol.
        Empty list if no contracts pass all filters.
    """
    if not symbols or buying_power <= 0:
        return []

    if config is None:
        config = ScreenerConfig()

    oi_min = config.options.options_oi_min
    spread_max = config.options.options_spread_max
    dte_min = config.options.dte_min
    dte_max = config.options.dte_max

    today = date.today()
    min_exp = today + timedelta(days=dte_min)
    max_exp = today + timedelta(days=dte_max)

    # Step 1: Fetch stock prices for buying power + OTM filtering
    stock_prices: dict[str, float] = {}
    affordable_symbols = symbols
    if stock_client is not None:
        try:
            req = StockLatestTradeRequest(symbol_or_symbols=symbols)
            latest_trades = stock_client.get_stock_latest_trade(req)
            stock_prices = {
                sym: float(latest_trades[sym].price)
                for sym in symbols
                if sym in latest_trades
            }
            affordable_symbols = [
                sym for sym in symbols
                if sym in stock_prices
                and 100 * stock_prices[sym] <= buying_power
            ]
        except Exception:
            logger.debug(
                "Failed to fetch latest trades for buying power filter; "
                "proceeding with all %d symbols",
                len(symbols),
            )
            affordable_symbols = symbols

    if not affordable_symbols:
        logger.debug(
            "No symbols affordable with buying power $%.2f", buying_power
        )
        return []

    logger.debug(
        "Buying power filter: %d/%d symbols affordable (bp=$%.2f)",
        len(affordable_symbols),
        len(symbols),
        buying_power,
    )

    # Step 2: Fetch put contracts with pagination
    try:
        req = GetOptionContractsRequest(
            underlying_symbols=affordable_symbols,
            type=ContractType.PUT,
            status=AssetStatus.ACTIVE,
            expiration_date_gte=min_exp,
            expiration_date_lte=max_exp,
            limit=1000,
        )

        all_contracts = []
        page_token = None

        while True:
            if page_token:
                req.page_token = page_token

            response = trade_client.get_option_contracts(req)
            contracts = response.option_contracts if response.option_contracts else []
            all_contracts.extend(contracts)

            page_token = getattr(response, "next_page_token", None)
            if not page_token:
                break

    except Exception:
        logger.debug(
            "Failed to fetch put contracts for %s",
            ", ".join(affordable_symbols),
        )
        return []

    if not all_contracts:
        logger.debug(
            "No put contracts found for %s in DTE range %d–%d",
            ", ".join(affordable_symbols),
            dte_min,
            dte_max,
        )
        return []

    # Step 3: Pre-filter by OI from contract data
    oi_passing = []
    for c in all_contracts:
        oi = int(c.open_interest) if c.open_interest is not None else 0
        if oi >= oi_min:
            oi_passing.append(c)

    if not oi_passing:
        logger.debug(
            "No put contracts with OI >= %d (checked %d contracts)",
            oi_min,
            len(all_contracts),
        )
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
        logger.debug("Failed to fetch snapshots for put contracts")
        return []

    # Step 5: Apply spread and delta filters, compute return
    candidates: list[PutRecommendation] = []

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

        # Compute spread (D034)
        midpoint = (bid + ask) / 2
        if midpoint <= 0:
            continue
        spread = (ask - bid) / midpoint

        # Spread filter
        if spread > spread_max:
            continue

        # Delta filter — puts have negative delta; None passes (D039)
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

        # Determine underlying symbol
        underlying = contract.underlying_symbol

        # OTM filter — puts must have strike below current stock price
        stock_price = stock_prices.get(underlying)
        if stock_price is not None and strike >= stock_price:
            continue

        # Compute extrinsic (time value) premium for ranking
        intrinsic = max(strike - stock_price, 0) if stock_price is not None else 0
        extrinsic = bid - intrinsic

        if extrinsic <= 0:
            continue

        ann_return = compute_put_annualized_return(extrinsic, strike, dte)
        if ann_return is None:
            continue

        candidates.append(
            PutRecommendation(
                symbol=contract.symbol,
                underlying=underlying,
                strike=strike,
                dte=dte,
                premium=bid,
                extrinsic=extrinsic,
                delta=delta,
                oi=oi,
                spread=spread,
                annualized_return=ann_return,
            )
        )

    # Step 7: One-per-underlying selection (keep best annualized return)
    best_per_underlying: dict[str, PutRecommendation] = {}
    for rec in candidates:
        existing = best_per_underlying.get(rec.underlying)
        if existing is None or rec.annualized_return > existing.annualized_return:
            best_per_underlying[rec.underlying] = rec

    # Step 8: Sort by annualized return descending
    recommendations = sorted(
        best_per_underlying.values(),
        key=lambda r: r.annualized_return,
        reverse=True,
    )

    logger.info(
        "Put screener: %d symbols screened, %d contracts fetched, "
        "%d passed filters, %d recommendations (one per underlying)",
        len(affordable_symbols),
        len(all_contracts),
        len(candidates),
        len(recommendations),
    )

    return recommendations


# ---------------------------------------------------------------------------
# Rich table display
# ---------------------------------------------------------------------------


def render_put_results_table(
    recommendations: list[PutRecommendation],
    buying_power: float,
    console: Optional[Console] = None,
) -> None:
    """Render a Rich table of cash-secured put recommendations.

    Args:
        recommendations: Sorted list of PutRecommendation objects.
        buying_power: Available buying power for header display.
        console: Optional Rich Console for output (D015 — testability).
    """
    console = console or _default_console

    if not recommendations:
        console.print(
            f"[yellow]No put recommendations found "
            f"(buying power ${buying_power:,.2f}).[/yellow]"
        )
        return

    table = Table(
        title=f"Cash-Secured Put Recommendations (Buying Power: ${buying_power:,.2f})",
        box=ROUNDED,
        header_style="bold cyan",
        row_styles=["", "dim"],
    )

    table.add_column("#", justify="right", style="dim", width=4, no_wrap=True)
    table.add_column("Symbol", style="bold", no_wrap=True)
    table.add_column("Underlying", no_wrap=True)
    table.add_column("Strike", justify="right")
    table.add_column("DTE", justify="right")
    table.add_column("Premium", justify="right")
    table.add_column("Extrinsic", justify="right")
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
            rec.underlying,
            f"${rec.strike:.2f}",
            str(rec.dte),
            f"${rec.premium:.2f}",
            f"${rec.extrinsic:.2f}",
            delta_str,
            f"{rec.oi:,}",
            spread_str,
            return_str,
        )

    console.print(table)
