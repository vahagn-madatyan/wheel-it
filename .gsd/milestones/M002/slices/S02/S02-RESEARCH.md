# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is a low-risk wiring slice. S01 (on branch `gsd/M002/S01`, not yet merged into S02) delivered `compute_monthly_performance()`, the `perf_1m` field on `ScreenedStock`, and the `top_n` parameter on `run_pipeline()` with full sort/cap logic and 12+ tests. S02's job is to (1) merge S01, (2) add a `--top-n` Typer CLI option to `scripts/run_screener.py` that passes through to `run_pipeline(top_n=N)`, (3) add a "Perf 1M" column to `render_results_table()` in `screener/display.py`, and (4) write tests for both.

All patterns are established — the CLI uses `typer.Option` with `Annotated` types, the display uses `table.add_column()` + `table.add_row()`, and the test suites (`test_cli_screener.py`, `test_display.py`) have clear patterns to follow. The only minor design choice is formatting: `fmt_pct` produces `3.1%` but TOPN-05 specifies signed format (`+3.1%`), so a dedicated `fmt_signed_pct` helper is warranted.

## Recommendation

Merge S01 into S02 first (prerequisite), then implement in two tasks:

- **T01:** `--top-n` CLI flag + tests — add Typer option, pass to `run_pipeline`, test flag parsing and backward compat
- **T02:** "Perf 1M" display column + formatter + tests — add `fmt_signed_pct`, add column to table, test rendering

Both tasks are small (~30 lines of production code each) and can share one test run for verification.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | Typer `typer.Option` | Already used for all 4 existing CLI options |
| Table rendering | Rich `Table` | Already used in `render_results_table` and `render_call_results_table` |
| Number formatting | `fmt_pct` in `screener/display.py` | Existing pattern; extend with signed variant for perf display |
| CLI testing | `typer.testing.CliRunner` | Already used in `test_cli_screener.py` |

## Existing Code and Patterns

### S01 Deliverables (branch `gsd/M002/S01`, must merge first)

- `models/screened_stock.py` line 40 — `perf_1m: Optional[float] = None` field added after `hv_percentile`
- `screener/market_data.py` — `compute_monthly_performance(bars_df)` returning float or None
- `screener/pipeline.py` line 1199 — `run_pipeline(..., top_n: int | None = None)` parameter; sorts Stage 1 survivors ascending by `perf_1m` (None→`float('inf')`), caps to `top_n` when set
- `tests/test_market_data.py` — 6 tests in `TestComputeMonthlyPerformance`
- `tests/test_pipeline.py` — `TestTopNPipelineCap` class with sort/cap/backward-compat tests

### CLI Pattern (`scripts/run_screener.py`)

- Uses `Annotated[type, typer.Option(...)]` for all parameters
- Enum for preset names (`PresetName(str, Enum)`)
- `run_pipeline()` called at line 119 with keyword args — add `top_n=top_n` there
- Tests in `test_cli_screener.py` use `typer.testing.CliRunner` + `@patch` decorators on module-level imports (D019)

### Display Pattern (`screener/display.py`)

- `render_results_table()` filters to `passed_all_filters and score is not None`, sorts by score desc
- Columns added via `table.add_column(name, justify, ...)` then `table.add_row(...)` in loop
- Current columns: #, Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, HV%ile, Yield, Score, Sector
- "Perf 1M" column should go before Score (after Yield, near HV%ile) for logical grouping of technical indicators
- Tests in `test_display.py` use `Console(file=StringIO())` to capture output, then assert on string content

### Formatting

- `fmt_pct(value)` → `"3.1%"` (no sign for positive) — used for RSI, Margin, Growth, Yield, HV%ile
- TOPN-05 requires signed format: `+3.1%`, `-5.2%` — need new `fmt_signed_pct` helper
- Existing `fmt_pct` must NOT be modified (would break existing column formatting where `+` is unwanted)

## Constraints

- S01 branch (`gsd/M002/S01`) must be merged into `gsd/M002/S02` before any implementation — S02 depends on `perf_1m` field, `top_n` parameter, and `compute_monthly_performance()`
- `top_n` CLI flag must be `Optional[int]` with default `None` — omitting flag means no cap (TOPN-06, D042)
- Typer 0.24.1 handles `int | None` with `typer.Option(default=None)` — no special handling needed
- 345 existing tests must continue passing after changes
- Console injection pattern (D015) must be used in any new display functions

## Common Pitfalls

- **Modifying `fmt_pct` for signed format** — Would add `+` prefix to RSI, Margin, Growth, Yield, HV%ile columns where it's unwanted. Create a separate `fmt_signed_pct` instead.
- **Forgetting to pass `top_n` through the CLI→pipeline call** — The `run_pipeline()` call at line 119 of `run_screener.py` currently has no `top_n` kwarg. Must add `top_n=top_n` after merging S01.
- **Column position in table** — "Perf 1M" must be added both as `add_column` AND as a value in every `add_row` call. Mismatch causes Rich to crash or silently skip data.
- **Test mock stack order** — `test_cli_screener.py` uses `@patch` decorators which apply bottom-up. Adding a new patch for `top_n` verification must respect this ordering.
- **Typer `--top-n` flag naming** — Typer converts underscores to hyphens automatically for CLI flags, but the Python parameter name should be `top_n`. The `typer.Option("--top-n", ...)` explicit name is safest.

## Open Risks

- None significant. All patterns are established, code paths are clear, and the feature is purely additive (no existing behavior changes).

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | — | none found (simple CLI option, no skill needed) |
| Rich | — | none found (simple table column, no skill needed) |

## Sources

- `scripts/run_screener.py` — CLI entry point with existing Typer option patterns
- `screener/display.py` — `render_results_table()` with column/row patterns
- `tests/test_cli_screener.py` — CLI test patterns with `CliRunner` + `@patch`
- `tests/test_display.py` — Display test patterns with `Console(file=StringIO())`
- `gsd/M002/S01` branch — S01 deliverables (pipeline `top_n`, `perf_1m` field, `compute_monthly_performance`)
- Decisions D015, D019, D042 — console injection, CLI import pattern, top_n CLI-only policy
