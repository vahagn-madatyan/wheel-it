# Phase 4: Output and Display - Research

**Researched:** 2026-03-08
**Domain:** Terminal UI rendering with Rich library (tables, panels, progress bars)
**Confidence:** HIGH

## Summary

Phase 4 builds a `screener/display.py` module containing three rendering functions and a progress callback factory, all using the Rich library. The data model (`ScreenedStock`, `FilterResult`) is already complete with all fields needed for display -- no model changes required. The pipeline (`run_pipeline()`) needs only a single parameter addition (`on_progress` callback).

Rich 14.3.3 is the current stable release, supports Python 3.8+, and provides `Table`, `Panel`, `Progress`, and `Console` classes that map directly to the three OUTP requirements. The callback pattern for progress uses Rich's `Progress.add_task()` / `Progress.update()` API, wrapped in a closure that the pipeline calls without depending on Rich itself.

**Primary recommendation:** Use Rich `Table` for results display, Rich `Panel` for stage summary, Rich `Table` again for per-filter breakdown, and Rich `Progress` with manual task management for the progress callback. All display functions accept an optional `Console` parameter for testability.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- 10 columns: Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, Score, Sector
- Compact number formatting: market cap as $2.1B, volume as 3.2M, price as $24.50, percentages with 1 decimal
- Show ALL passing stocks (no top-N cap), numbered rows, sorted by score descending
- Color-coded scores: green for top-third, yellow for middle-third, red for bottom-third
- Rich Table with styled headers
- Two rendering functions: `render_stage_summary()` (compact Rich Panel) and `render_filter_breakdown()` (per-filter table)
- Phase 5 wires --verbose flag to select between them (stage summary default, per-filter for verbose)
- Both use Rich formatting (Panel for stage summary, Table for per-filter breakdown)
- Per-stage Rich progress bars via callback injection into run_pipeline()
- Stages: Fetching Alpaca bars, Filtering Stage 1, Fetching Finnhub data, Filtering Stage 2, Scoring
- Finnhub stage shows current symbol name alongside the progress bar
- Progress callback is optional parameter on run_pipeline(); pipeline stays testable without Rich dependency
- Callback signature: `on_progress(stage, current, total, symbol=None)`
- New module: `screener/display.py`
- Pipeline returns data only (list[ScreenedStock]) -- caller handles display
- Display functions accept optional `Console` parameter (defaults to global Console) for testability
- Progress callback provided by the display module, passed into pipeline by CLI caller (Phase 5)
- Rich library added as project dependency in pyproject.toml

### Claude's Discretion
- Exact Rich Table styling (border style, padding, header colors)
- Progress bar column layout and refresh rate
- How to handle edge cases (0 passing stocks, very long sector names, None values in table cells)
- Internal helper functions for number formatting

### Deferred Ideas (OUT OF SCOPE)
- --verbose flag wiring to select stage summary vs per-filter breakdown -- Phase 5 CLI integration
- v2 OUTP-05: Options chain preview alongside each result
- v2 OUTP-06: --dry-run mode showing what would change in symbol_list.txt
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| OUTP-01 | Screener displays results as a rich formatted table showing symbol, price, volume, key metrics, and score | Rich Table class with add_column/add_row API; number formatting helpers; color-coded score styling using style strings |
| OUTP-02 | Screener shows filter summary with per-stage elimination counts | Two functions: `render_stage_summary()` using Rich Panel with formatted text; `render_filter_breakdown()` using Rich Table with waterfall counts |
| OUTP-04 | Screener shows progress indicator during rate-limited API calls | Rich Progress with manual task management; callback closure pattern; `on_progress` parameter injected into `run_pipeline()` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rich | >=14.0 | Terminal table, panel, progress rendering | De facto Python terminal UI library; 50k+ GitHub stars; stable API since v12 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rich.table.Table | (part of rich) | Results table and filter breakdown table | OUTP-01 and OUTP-02 per-filter view |
| rich.panel.Panel | (part of rich) | Stage summary bordered box | OUTP-02 stage summary view |
| rich.progress.Progress | (part of rich) | Progress bars during pipeline | OUTP-04 progress indicator |
| rich.console.Console | (part of rich) | Output target; testability via StringIO injection | All display functions |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| rich | tabulate + tqdm | Two deps instead of one; no unified styling; tqdm progress doesn't compose with tables |
| rich | click.echo + ASCII | No color, no box drawing, no progress; significant hand-rolling |

**Installation:**
```bash
uv pip install rich
```

Also add to `pyproject.toml` dependencies list:
```toml
dependencies = [
    # existing deps...
    "rich>=14.0",
]
```

## Architecture Patterns

### Recommended Project Structure
```
screener/
├── __init__.py
├── config_loader.py     # existing
├── finnhub_client.py    # existing
├── market_data.py       # existing
├── pipeline.py          # existing (add on_progress callback)
└── display.py           # NEW: all rendering functions
```

### Pattern 1: Display Module with Optional Console
**What:** All display functions accept `console: Console | None = None` and default to a module-level `Console()`.
**When to use:** Every public function in `display.py`.
**Example:**
```python
# Source: Rich official docs - Console
from rich.console import Console

_default_console = Console()

def render_results_table(
    stocks: list[ScreenedStock],
    console: Console | None = None,
) -> None:
    console = console or _default_console
    # ... build and print table
```

### Pattern 2: Callback Closure for Progress
**What:** `display.py` provides a factory function `create_progress_callback()` that returns both a `Progress` context manager and a callback function. The pipeline calls `on_progress(stage, current, total, symbol=None)` without knowing about Rich.
**When to use:** Decoupling pipeline from Rich dependency.
**Example:**
```python
# Source: Rich official docs - Progress
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn

def create_progress_callback(console: Console | None = None):
    """Returns (progress_context, callback_fn).

    Caller enters progress_context, then passes callback_fn to run_pipeline.
    """
    console = console or _default_console
    progress = Progress(
        TextColumn("{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    )
    tasks: dict[str, int] = {}  # stage_name -> task_id

    def on_progress(stage: str, current: int, total: int, symbol: str | None = None):
        desc = stage if symbol is None else f"{stage} ({symbol})"
        if stage not in tasks:
            tasks[stage] = progress.add_task(desc, total=total)
        task_id = tasks[stage]
        progress.update(task_id, completed=current, description=desc)

    return progress, on_progress
```

### Pattern 3: Number Formatting Helpers
**What:** Pure helper functions for compact number display. No Rich dependency.
**When to use:** Converting raw floats to display strings in the table.
**Example:**
```python
def fmt_large_number(value: float | None, prefix: str = "$") -> str:
    """Format large numbers: 2100000000 -> '$2.1B', 3200000 -> '3.2M'."""
    if value is None:
        return "N/A"
    abs_val = abs(value)
    if abs_val >= 1_000_000_000:
        return f"{prefix}{value / 1_000_000_000:.1f}B"
    if abs_val >= 1_000_000:
        return f"{prefix}{value / 1_000_000:.1f}M"
    if abs_val >= 1_000:
        return f"{prefix}{value / 1_000:.1f}K"
    return f"{prefix}{value:.0f}"

def fmt_price(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"${value:.2f}"

def fmt_pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}%"

def fmt_ratio(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}"
```

### Pattern 4: Score Color by Thirds
**What:** Compute color thresholds from the actual score distribution, not fixed cutoffs.
**When to use:** When adding score values to the results table.
**Example:**
```python
def _score_style(score: float, all_scores: list[float]) -> str:
    """Return 'green', 'yellow', or 'red' based on score's position in distribution."""
    if not all_scores:
        return "white"
    sorted_scores = sorted(all_scores)
    n = len(sorted_scores)
    low_cutoff = sorted_scores[n // 3] if n >= 3 else sorted_scores[0]
    high_cutoff = sorted_scores[2 * n // 3] if n >= 3 else sorted_scores[-1]
    if score >= high_cutoff:
        return "green"
    elif score >= low_cutoff:
        return "yellow"
    else:
        return "red"
```

### Anti-Patterns to Avoid
- **Importing Rich in pipeline.py:** The pipeline must remain testable without Rich. Only `display.py` imports Rich; the pipeline accepts a plain callable callback.
- **Using `rich.print()` globally:** Use explicit `Console` instances, not the module-level `rich.print`. This makes testing possible.
- **Hardcoded score color thresholds:** Use distribution-based thirds, not fixed values like "above 70 = green".
- **Building strings then printing:** Use Rich's structured API (Table.add_row, Panel) rather than string concatenation with ANSI codes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Table formatting | Custom ASCII table renderer | `rich.Table` | Column alignment, wrapping, Unicode borders, terminal width handling |
| Progress bars | Custom print-and-carriage-return loop | `rich.Progress` | Terminal refresh, ETA calculation, multi-task support |
| Bordered boxes | Manual box-drawing characters | `rich.Panel` | Automatic width, title/subtitle, composable with other renderables |
| Terminal color codes | ANSI escape sequences | Rich style strings | Cross-platform, degrades gracefully on dumb terminals |

**Key insight:** Terminal rendering has edge cases (terminal width, Unicode support, Windows terminals, piped output) that Rich handles transparently. Hand-rolling any of these means re-solving problems Rich has already solved.

## Common Pitfalls

### Pitfall 1: Logging Package Shadow
**What goes wrong:** `import logging` in `display.py` imports the project's `logging/` package instead of stdlib.
**Why it happens:** The project has a `logging/` directory that shadows Python's stdlib `logging` module.
**How to avoid:** Use `import logging as stdlib_logging` in `display.py`, consistent with the pattern already established in `pipeline.py` and other modules.
**Warning signs:** `AttributeError: module 'logging' has no attribute 'getLogger'` at import time.

### Pitfall 2: Progress Context Manager Lifecycle
**What goes wrong:** Progress bars render in the wrong order, overlap with table output, or leave artifacts.
**Why it happens:** Rich Progress uses a Live display that takes control of the terminal. If you print() while Progress is active, output gets mangled.
**How to avoid:** Enter Progress context manager only during pipeline execution, exit before printing results table. Never call `console.print()` while Progress is active.
**Warning signs:** Garbled terminal output, progress bars appearing after results.

### Pitfall 3: None Values in Table Cells
**What goes wrong:** `TypeError` when formatting None values, or "None" string appearing in table cells.
**Why it happens:** Stocks that fail early filters have None for fundamental/technical fields that still display in the table.
**How to avoid:** All formatting helpers must handle `None` -> `"N/A"` as first check. Only passing stocks are shown in the results table (per CONTEXT.md: "show ALL passing stocks"), but defensive handling is still wise.
**Warning signs:** Crashes on stocks with missing Finnhub data.

### Pitfall 4: Score Distribution with Few Stocks
**What goes wrong:** Division-by-thirds fails when fewer than 3 stocks pass.
**Why it happens:** `sorted_scores[n // 3]` with n=1 or n=2 produces edge cases.
**How to avoid:** Handle special cases: 0 stocks = no table, 1-2 stocks = all green (or a neutral color).
**Warning signs:** IndexError or all stocks same color regardless of scores.

### Pitfall 5: Pipeline Callback Placement
**What goes wrong:** Callback fires at wrong times or misses stages.
**Why it happens:** `run_pipeline()` has a clear sequential flow, but the callback injection points need to match the stage boundaries precisely.
**How to avoid:** Map callback calls to specific lines in `run_pipeline()`:
  1. After `fetch_daily_bars()` -> "Fetching Alpaca bars" complete
  2. Inside the per-symbol loop before `run_stage_1_filters()` -> "Filtering Stage 1" progress
  3. Before each `run_stage_2_filters()` call -> "Fetching Finnhub data" with symbol name
  4. After Stage 2 loop completes -> "Filtering Stage 2" complete
  5. After scoring loop -> "Scoring" complete
**Warning signs:** Progress bar stalls at certain percentages, or never reaches 100%.

### Pitfall 6: Terminal Width with 10 Columns
**What goes wrong:** Table wraps or truncates on narrow terminals (< 120 chars).
**Why it happens:** 10 columns with labels can exceed 100 characters easily.
**How to avoid:** Use `no_wrap=True` on symbol column, keep headers short, use compact number formatting. Rich handles overflow gracefully by default (wrapping long cells), but test at 80-char width.
**Warning signs:** Table looks garbled in standard 80-column terminal.

## Code Examples

Verified patterns from official sources:

### Results Table (OUTP-01)
```python
# Source: Rich official docs - Tables
from rich.table import Table
from rich.console import Console
from rich import box

def render_results_table(
    stocks: list[ScreenedStock],
    console: Console | None = None,
) -> None:
    console = console or _default_console
    passing = [s for s in stocks if s.passed_all_filters and s.score is not None]
    passing.sort(key=lambda s: s.score, reverse=True)

    if not passing:
        console.print("[yellow]No stocks passed all filters.[/yellow]")
        return

    all_scores = [s.score for s in passing]

    table = Table(
        title="Screening Results",
        box=box.ROUNDED,
        header_style="bold cyan",
        row_styles=["", "dim"],
    )

    table.add_column("#", justify="right", style="dim", width=4)
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

    for i, stock in enumerate(passing, 1):
        score_style = _score_style(stock.score, all_scores)
        table.add_row(
            str(i),
            stock.symbol,
            fmt_price(stock.price),
            fmt_large_number(stock.avg_volume, prefix=""),
            fmt_large_number(stock.market_cap),
            fmt_ratio(stock.debt_equity),
            fmt_pct(stock.net_margin),
            fmt_pct(stock.sales_growth),
            fmt_pct(stock.rsi_14),
            f"[{score_style}]{stock.score:.1f}[/{score_style}]",
            stock.sector or "N/A",
        )

    console.print(table)
```

### Stage Summary Panel (OUTP-02 compact view)
```python
# Source: Rich official docs - Panel
from rich.panel import Panel
from rich.text import Text

def render_stage_summary(
    stocks: list[ScreenedStock],
    console: Console | None = None,
) -> None:
    console = console or _default_console
    total = len(stocks)
    # Count by stage
    no_bars = sum(1 for s in stocks if any(r.filter_name == "bar_data" for r in s.filter_results))
    had_bars = total - no_bars
    # Stage 1 pass = those who have stage 2 filter results (or passed all)
    stage1_names = {"price_range", "avg_volume", "rsi", "sma200"}
    stage2_names = {"market_cap", "debt_equity", "net_margin", "sales_growth", "sector", "optionable"}

    passed_stage1 = sum(
        1 for s in stocks
        if all(r.passed for r in s.filter_results if r.filter_name in stage1_names)
        and any(r.filter_name in stage1_names for r in s.filter_results)
    )
    passed_stage2 = sum(1 for s in stocks if s.passed_all_filters)
    scored = sum(1 for s in stocks if s.score is not None)

    lines = [
        f"  Universe:     {total:>6,}",
        f"  After bars:   {had_bars:>6,}  (-{no_bars:,})",
        f"  Stage 1:      {passed_stage1:>6,}  (-{had_bars - passed_stage1:,})",
        f"  Stage 2:      {passed_stage2:>6,}  (-{passed_stage1 - passed_stage2:,})",
        f"  Scored:       {scored:>6,}",
    ]

    panel = Panel(
        "\n".join(lines),
        title="Filter Summary",
        border_style="blue",
        expand=False,
    )
    console.print(panel)
```

### Per-Filter Breakdown Table (OUTP-02 verbose view)
```python
# Source: Rich official docs - Tables
def render_filter_breakdown(
    stocks: list[ScreenedStock],
    console: Console | None = None,
) -> None:
    console = console or _default_console
    # Build waterfall: for each filter, count how many removed
    filter_order = [
        "bar_data", "price_range", "avg_volume", "rsi", "sma200",
        "market_cap", "debt_equity", "net_margin", "sales_growth",
        "sector", "optionable",
    ]

    table = Table(
        title="Filter Breakdown",
        box=box.SIMPLE_HEAVY,
        header_style="bold",
    )
    table.add_column("Filter", style="cyan")
    table.add_column("Removed", justify="right", style="red")
    table.add_column("Remaining", justify="right", style="green")

    remaining = len(stocks)
    for fname in filter_order:
        failed = sum(
            1 for s in stocks
            if any(r.filter_name == fname and not r.passed for r in s.filter_results)
        )
        remaining -= failed
        if failed > 0:
            table.add_row(fname, str(failed), str(remaining))

    console.print(table)
```

### Progress Callback Factory (OUTP-04)
```python
# Source: Rich official docs - Progress
from rich.progress import (
    Progress, TextColumn, BarColumn,
    TaskProgressColumn, TimeRemainingColumn, SpinnerColumn,
)
from typing import Callable, Protocol
from contextlib import contextmanager

# Callback type for pipeline (no Rich dependency)
ProgressCallback = Callable[[str, int, int], None]  # stage, current, total

@contextmanager
def progress_context(console: Console | None = None):
    """Yields (progress_display, callback_fn) for use with run_pipeline."""
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

    def callback(stage: str, current: int, total: int, symbol: str | None = None):
        desc = f"{stage} [dim]({symbol})[/dim]" if symbol else stage
        if stage not in tasks:
            tasks[stage] = progress.add_task(desc, total=total)
        progress.update(tasks[stage], completed=current, description=desc)

    with progress:
        yield callback
```

### Pipeline Callback Integration Point
```python
# In pipeline.py run_pipeline() -- add on_progress parameter:
def run_pipeline(
    trade_client,
    stock_client,
    finnhub_client: FinnhubClient,
    config: ScreenerConfig,
    symbol_list_path: str = "config/symbol_list.txt",
    on_progress: Callable | None = None,  # NEW
) -> list[ScreenedStock]:
    # Helper to safely call callback
    def _progress(stage, current, total, symbol=None):
        if on_progress:
            on_progress(stage, current, total, symbol=symbol)

    # ... existing Step 1-2 code ...

    # Step 3: after bars fetched
    bars = fetch_daily_bars(stock_client, universe, num_bars=250, batch_size=20)
    _progress("Fetching Alpaca bars", len(universe), len(universe))

    # Step 4-5: per-symbol loop
    for i, sym in enumerate(universe):
        _progress("Filtering Stage 1", i + 1, len(universe))
        # ... existing code ...
        if stage1_passed:
            _progress("Fetching Finnhub data", i + 1, len(universe), symbol=sym)
            run_stage_2_filters(stock, config, finnhub_client, optionable_set)

    # Step 6: scoring
    _progress("Scoring", len(passing), len(passing))
    # ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| colorama + tabulate | rich (unified) | 2020+ | Single dependency for colors, tables, progress, panels |
| tqdm for progress | rich.progress | 2021+ | Composable with Rich's other renderables |
| print() with f-strings | Console.print() with markup | Since Rich v1 | Testable, styled, handles terminal width |

**Deprecated/outdated:**
- `rich.traceback.install()` auto-installs globally -- not relevant here, but don't accidentally import it
- `from rich import print` overrides builtins -- avoid, use explicit Console instead

## Open Questions

1. **Exact progress stage boundaries in pipeline**
   - What we know: `run_pipeline()` has clear sequential stages (fetch bars, Stage 1, Stage 2, score)
   - What's unclear: Stage 1 and Stage 2 overlap in the per-symbol loop -- should progress show one bar per stage, or a single bar for the entire loop with sub-stages?
   - Recommendation: Use separate task IDs per stage. "Filtering Stage 1" advances per symbol. "Fetching Finnhub data" advances only for symbols that pass Stage 1. This matches the user's spec for per-stage bars.

2. **Sector column truncation**
   - What we know: Finnhub industry names can be long (e.g., "Semiconductors & Semiconductor Equipment")
   - What's unclear: How Rich handles `max_width` truncation display
   - Recommendation: Set `max_width=20` on Sector column. Rich truncates with ellipsis automatically.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via `python -m pytest`) |
| Config file | none (default discovery) |
| Quick run command | `python -m pytest tests/test_display.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OUTP-01 | Results table renders with 10 columns, numbered rows, score colors | unit | `python -m pytest tests/test_display.py::TestRenderResultsTable -x` | Wave 0 |
| OUTP-01 | Number formatting (price, volume, market cap, percentages) | unit | `python -m pytest tests/test_display.py::TestFormatters -x` | Wave 0 |
| OUTP-01 | Edge case: 0 passing stocks shows message, no crash | unit | `python -m pytest tests/test_display.py::TestRenderResultsTable::test_empty_results -x` | Wave 0 |
| OUTP-02 | Stage summary panel shows correct counts | unit | `python -m pytest tests/test_display.py::TestRenderStageSummary -x` | Wave 0 |
| OUTP-02 | Per-filter breakdown table shows waterfall counts | unit | `python -m pytest tests/test_display.py::TestRenderFilterBreakdown -x` | Wave 0 |
| OUTP-04 | Progress callback factory produces callable | unit | `python -m pytest tests/test_display.py::TestProgressCallback -x` | Wave 0 |
| OUTP-04 | run_pipeline() accepts on_progress and calls it at stage boundaries | unit | `python -m pytest tests/test_pipeline.py::TestRunPipelineProgress -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_display.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_display.py` -- covers OUTP-01, OUTP-02, OUTP-04 display functions
- [ ] Rich library install: `uv pip install rich` -- not currently in dependencies
- [ ] Test strategy: Use `Console(file=StringIO(), width=120)` to capture output for assertions without terminal dependency

### Testing Approach
All display functions can be tested without a real terminal by injecting a `Console(file=StringIO(), width=120)` instance. Tests verify:
- Table contains expected column headers and data values (substring match on captured output)
- Correct row count in output
- Score colors appear in markup (check for `[green]`, `[yellow]`, `[red]` in raw output before stripping)
- Number formatting helper functions are pure and test independently
- Progress callback can be called without errors (verify it doesn't raise)

## Sources

### Primary (HIGH confidence)
- [Rich official docs - Console](https://rich.readthedocs.io/en/stable/console.html) - Console API, testability patterns (StringIO, capture)
- [Rich official docs - Tables](https://rich.readthedocs.io/en/stable/tables.html) - Table API, add_column, add_row, box styles, row_styles
- [Rich official docs - Panel](https://rich.readthedocs.io/en/stable/panel.html) - Panel API, title, subtitle, expand, border_style
- [Rich official docs - Progress](https://rich.readthedocs.io/en/stable/progress.html) - Progress API, add_task, update, manual task management, column types
- [Rich official docs - Style](https://rich.readthedocs.io/en/stable/style.html) - Style strings, colors, bold/dim, combining styles
- [PyPI - rich 14.3.3](https://pypi.org/project/rich/) - Current version, Python 3.8+ support

### Secondary (MEDIUM confidence)
- Existing codebase patterns (`pipeline.py`, `models/screened_stock.py`) - verified by direct code reading

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Rich is the uncontested standard for Python terminal UI; verified current version on PyPI
- Architecture: HIGH - Callback pattern, Console injection, and display module structure follow Rich's documented patterns and project conventions
- Pitfalls: HIGH - Logging shadow is a known project pattern; Progress lifecycle is well-documented; None handling is standard practice
- Code examples: HIGH - All examples based on official Rich documentation patterns applied to verified data model fields

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (Rich API is very stable; major version has been 13-14 for years)
