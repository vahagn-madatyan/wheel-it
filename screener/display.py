"""Rich-formatted terminal output for screening results and filter summaries."""

from __future__ import annotations

import logging as stdlib_logging
from contextlib import contextmanager
from typing import Callable, Optional

from rich.box import ROUNDED, SIMPLE_HEAVY
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from models.screened_stock import FilterResult, ScreenedStock

_default_console = Console()
logger = stdlib_logging.getLogger(__name__)

ProgressCallback = Callable[[str, int, int], None]


# ---------------------------------------------------------------------------
# Progress indicator
# ---------------------------------------------------------------------------


@contextmanager
def progress_context(console: Console | None = None):
    """Context manager yielding a progress callback for pipeline stages.

    The yielded callback has the signature::

        callback(stage: str, current: int, total: int, symbol: str | None = None)

    Each unique *stage* name creates a new Rich progress bar.  Subsequent
    calls with the same *stage* update the existing bar.  When *symbol* is
    provided, it is shown alongside the stage description.

    Args:
        console: Optional Rich Console for output.  Falls back to module
            default if not provided.

    Yields:
        A callable matching the ``on_progress`` signature expected by
        :func:`screener.pipeline.run_pipeline`.
    """
    console = console or _default_console
    progress = Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    )
    tasks: dict[str, int] = {}

    def callback(
        stage: str,
        current: int,
        total: int,
        symbol: str | None = None,
    ) -> None:
        desc = f"{stage} [dim]({symbol})[/dim]" if symbol else stage
        if stage not in tasks:
            tasks[stage] = progress.add_task(desc, total=total)
        progress.update(tasks[stage], completed=current, description=desc)

    with progress:
        yield callback


# ---------------------------------------------------------------------------
# Number formatting helpers
# ---------------------------------------------------------------------------


def fmt_large_number(value: float | None, prefix: str = "$") -> str:
    """Format large numbers compactly: $2.1B, 3.2M, $45.0K."""
    if value is None:
        return "N/A"
    abs_val = abs(value)
    sign = "-" if value < 0 else ""
    if abs_val >= 1_000_000_000:
        return f"{sign}{prefix}{abs_val / 1_000_000_000:.1f}B"
    if abs_val >= 1_000_000:
        return f"{sign}{prefix}{abs_val / 1_000_000:.1f}M"
    if abs_val >= 1_000:
        return f"{sign}{prefix}{abs_val / 1_000:.1f}K"
    return f"{sign}{prefix}{abs_val:.1f}"


def fmt_price(value: float | None) -> str:
    """Format price as $X.XX."""
    if value is None:
        return "N/A"
    return f"${value:.2f}"


def fmt_pct(value: float | None) -> str:
    """Format percentage as X.X%."""
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def fmt_ratio(value: float | None) -> str:
    """Format ratio as X.XX."""
    if value is None:
        return "N/A"
    return f"{value:.2f}"


# ---------------------------------------------------------------------------
# Score color styling
# ---------------------------------------------------------------------------


def _score_style(score: float, all_scores: list[float]) -> str:
    """Return Rich style name based on score position in distribution.

    Distributes into thirds: top -> green, middle -> yellow, bottom -> red.
    """
    if not all_scores:
        return "white"
    if len(all_scores) < 3:
        return "green"

    sorted_scores = sorted(all_scores)
    n = len(sorted_scores)
    low_cutoff = sorted_scores[n // 3]
    high_cutoff = sorted_scores[2 * n // 3]

    if score >= high_cutoff:
        return "green"
    if score >= low_cutoff:
        return "yellow"
    return "red"


# ---------------------------------------------------------------------------
# Results table
# ---------------------------------------------------------------------------


def render_results_table(
    stocks: list[ScreenedStock],
    console: Console | None = None,
) -> None:
    """Render a Rich table of screening results.

    Shows only stocks that passed all filters and have a score.
    Rows are numbered and sorted by score descending.
    """
    console = console or _default_console

    passing = [s for s in stocks if s.passed_all_filters and s.score is not None]
    passing.sort(key=lambda s: s.score, reverse=True)  # type: ignore[arg-type]

    if not passing:
        console.print("[yellow]No stocks passed all filters.[/yellow]")
        return

    all_scores = [s.score for s in passing]  # type: ignore[misc]

    table = Table(
        title="Screening Results",
        box=ROUNDED,
        header_style="bold cyan",
        row_styles=["", "dim"],
    )

    table.add_column("#", justify="right", style="dim", width=4, no_wrap=True)
    table.add_column("Symbol", style="bold", no_wrap=True)
    table.add_column("Price", justify="right")
    table.add_column("AvgVol", justify="right")
    table.add_column("MktCap", justify="right")
    table.add_column("D/E", justify="right")
    table.add_column("Margin", justify="right")
    table.add_column("Growth", justify="right")
    table.add_column("RSI", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Sector", max_width=20)

    for idx, stock in enumerate(passing, start=1):
        style = _score_style(stock.score, all_scores)
        score_str = f"[{style}]{stock.score:.1f}[/{style}]"

        table.add_row(
            str(idx),
            stock.symbol,
            fmt_price(stock.price),
            fmt_large_number(stock.avg_volume, prefix=""),
            fmt_large_number(stock.market_cap),
            fmt_ratio(stock.debt_equity),
            fmt_pct(stock.net_margin),
            fmt_pct(stock.sales_growth),
            fmt_pct(stock.rsi_14),
            score_str,
            stock.sector or "N/A",
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Filter elimination summaries
# ---------------------------------------------------------------------------


def render_stage_summary(
    stocks: list[ScreenedStock],
    console: Console | None = None,
) -> None:
    """Render a panel showing stock counts at each filtering stage."""
    console = console or _default_console

    total = len(stocks)

    # Stage 0: after bar_data
    had_bars = sum(
        1 for s in stocks
        if not any(f.filter_name == "bar_data" and not f.passed for f in s.filter_results)
    )

    # Stage 1 filters
    stage1_names = {"price_range", "avg_volume", "rsi", "sma200"}
    stage1_pass = sum(
        1 for s in stocks
        if not any(f.filter_name == "bar_data" and not f.passed for f in s.filter_results)
        and all(
            f.passed for f in s.filter_results if f.filter_name in stage1_names
        )
        and any(f.filter_name in stage1_names for f in s.filter_results)
    )

    # Stage 2: passed all filters
    stage2_pass = sum(1 for s in stocks if s.passed_all_filters)

    # Scored
    scored = sum(1 for s in stocks if s.passed_all_filters and s.score is not None)

    bar_removed = total - had_bars
    s1_removed = had_bars - stage1_pass
    s2_removed = stage1_pass - stage2_pass
    score_removed = stage2_pass - scored

    lines = [
        f"  Universe:    {total:>5}",
        f"  After bars:  {had_bars:>5}  (-{bar_removed})",
        f"  Stage 1:     {stage1_pass:>5}  (-{s1_removed})",
        f"  Stage 2:     {stage2_pass:>5}  (-{s2_removed})",
        f"  Scored:      {scored:>5}  (-{score_removed})",
    ]

    panel = Panel(
        "\n".join(lines),
        title="Filter Summary",
        border_style="blue",
        expand=False,
    )
    console.print(panel)


def render_filter_breakdown(
    stocks: list[ScreenedStock],
    console: Console | None = None,
) -> None:
    """Render a per-filter waterfall table showing how many stocks each filter removed."""
    console = console or _default_console

    filter_order = [
        "bar_data",
        "price_range", "avg_volume", "rsi", "sma200",
        "market_cap", "debt_equity", "net_margin", "sales_growth", "sector", "optionable",
    ]

    table = Table(
        title="Filter Breakdown",
        box=SIMPLE_HEAVY,
        header_style="bold",
    )
    table.add_column("Filter", style="cyan")
    table.add_column("Removed", justify="right", style="red")
    table.add_column("Remaining", justify="right", style="green")

    remaining = len(stocks)

    for fname in filter_order:
        failed = sum(
            1 for s in stocks
            if any(f.filter_name == fname and not f.passed for f in s.filter_results)
        )
        if failed > 0:
            remaining -= failed
            table.add_row(fname, str(failed), str(remaining))

    console.print(table)
