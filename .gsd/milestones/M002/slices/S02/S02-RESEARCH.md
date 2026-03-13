# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 is a low-risk wiring slice connecting S01's pipeline internals to user-visible surfaces: a `--top-n` CLI flag on `run-screener` and a "Perf 1M" column in the Rich results table. All heavy lifting (perf computation, sort/cap logic, two-pass pipeline) lives in S01 on branch `gsd/M002/S01` and must be merged before S02 work begins.

The implementation touches exactly three files (`scripts/run_screener.py`, `screener/display.py`, `tests/`) with well-established patterns to follow. Both the CLI and display changes are purely additive — no existing behavior changes. The 345 existing tests pass on the current branch and should remain green.

The one formatting nuance: TOPN-05 requires explicit sign on "Perf 1M" values (`-5.2%`, `+3.1%`), but the existing `fmt_pct()` helper only shows sign for negative values. A small `fmt_pct_signed()` helper or inline `f"{value:+.1f}%"` handles this.

## Recommendation

1. **Merge S01 branch first** — `git merge gsd/M002/S01` into `gsd/M002/S02` to get `perf_1m` field, `compute_monthly_performance()`, and `run_pipeline(top_n=)` parameter. S01 diff is clean: 16 files changed, only `models/screened_stock.py` (+1 line), `screener/market_data.py` (+17 lines), `screener/pipeline.py` (refactored 84 lines), plus tests and GSD artifacts.
2. **Add `--top-n` CLI option** — Follow the existing `Annotated[..., typer.Option(...)]` pattern. Pass through to `run_pipeline(top_n=top_n)`. Use `min=1` (confirmed supported by installed Typer version).
3. **Add "Perf 1M" column** — Insert between "HV%ile" and "Yield" in `render_results_table()`. Use a signed-percent formatter.
4. **Test both surfaces** — CLI flag test via `typer.testing.CliRunner`; display column test via `Console(file=StringIO())` capture.

## Requirements Owned by This Slice

| Requirement | Role | What S02 Must Deliver |
|-------------|------|-----------------------|
| TOPN-01 | primary | `--top-n N` CLI flag that passes through to `run_pipeline(top_n=N)` |
| TOPN-05 | primary | "Perf 1M" column in Rich results table with signed percentage format |
| TOPN-06 | primary | No flag = `top_n=None` = all stocks processed (backward compatible) |

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | `typer.Option` with `Annotated` type hints | Already used for `--verbose`, `--preset`, `--config`, `--update-symbols` — consistent pattern |
| Table rendering | `rich.table.Table` with `add_column` / `add_row` | Already used for 13 columns in `render_results_table()` |
| Number formatting | `fmt_pct()` in `screener/display.py` | Handles `None → "N/A"` and `%.1f%` formatting; extend for sign |
| CLI testing | `typer.testing.CliRunner` | Used in all 5 existing CLI tests in `test_cli_screener.py` |
| Display testing | `Console(file=StringIO(), width=120)` capture | Used in all 17 existing display tests in `test_display.py` |

## Existing Code and Patterns

- `scripts/run_screener.py:55-73` — CLI option pattern: `Annotated[type | None, typer.Option("--flag", help="...")]` with default `= None` or `= False`. S02's `--top-n` follows this exactly.
- `scripts/run_screener.py:119-126` — `run_pipeline()` call site. S02 adds `top_n=top_n` kwarg here. Currently passes `trade_client`, `stock_client`, `finnhub`, `cfg`, `on_progress`, and `option_client`.
- `screener/display.py:169-193` — Column definitions in `render_results_table()`. 13 columns: `#, Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, HV%ile, Yield, Score, Sector`. S02 inserts "Perf 1M" after "HV%ile" (position 10) and before "Yield" (shifts from position 11 to 12).
- `screener/display.py:195-215` — Row construction via `add_row()`. S02 adds `perf_1m` value at corresponding position in the argument list.
- `screener/display.py:107-118` — `fmt_pct()` helper: `f"{value:.1f}%"` or `"N/A"`. No `+` prefix on positive values. S02 needs a signed variant: `f"{value:+.1f}%"`.
- `tests/test_cli_screener.py:36-74` — `test_default_no_file_writes`: canonical CLI test — patches 8 dependencies, invokes via `CliRunner`, asserts `run_pipeline` was called and display functions invoked. S02 follows this pattern.
- `tests/test_display.py:30-57` — `_make_stock()` helper: creates `ScreenedStock` with keyword fields. Currently accepts `symbol, filter_results, score, price, avg_volume, market_cap, debt_equity, net_margin, sales_growth, rsi_14, sector`. Does NOT accept `perf_1m` or `hv_percentile` — S02 tests need to set `perf_1m` directly on the stock object or extend the helper.
- `tests/test_display.py:60-66` — `_all_pass_filters()`: returns passing `FilterResult` list. Reuse as-is.
- `tests/test_options_chain.py:634-680` — `TestDisplayYieldColumn`: display test pattern for a column added by a later slice. Creates a stock, appends a filter result, renders table, asserts column header and formatted value both appear in output. This is the exact pattern S02 should follow for "Perf 1M".

## Constraints

- **S01 must be merged first.** S02 depends on `ScreenedStock.perf_1m` field, `compute_monthly_performance()`, and `run_pipeline(top_n=)` — all on branch `gsd/M002/S01`. Merge is expected to be conflict-free: S01 only modified `pipeline.py`, `market_data.py`, `screened_stock.py`, and test files.
- **`top_n` must be `int | None`, default `None`.** Per D042, `None` means no cap (backward compatible, TOPN-06). Typer handles `int | None` natively with default `None`.
- **`top_n` must be positive when set.** Use `typer.Option(min=1)` — confirmed this parameter exists in the installed Typer version (0.12+).
- **Column insert position.** "Perf 1M" goes after "HV%ile" and before "Yield" in both `add_column()` and `add_row()` calls. Currently 13 values in `add_row()`, will become 14. Mismatch between column count and row values causes a silent misalignment — count carefully.
- **Signed format for Perf 1M.** TOPN-05 says `-5.2%`, `+3.1%`. Python's `f"{value:+.1f}%"` produces this natively. For `None`, return `"N/A"`.
- **345 existing tests must continue to pass.** S02 changes are additive — no existing function signatures change.

## Common Pitfalls

- **Forgetting to merge S01 first** — `perf_1m` field doesn't exist on `ScreenedStock` on the current branch. Any code referencing it will AttributeError. Merge `gsd/M002/S01` as the first step.
- **Using `fmt_pct()` directly for Perf 1M** — `fmt_pct(-5.2)` → `"-5.2%"` (correct), but `fmt_pct(3.1)` → `"3.1%"` (missing `+`). Need either a new `fmt_pct_signed()` or inline `f"{value:+.1f}%"` with `None` guard.
- **Column/row position mismatch** — Adding `add_column("Perf 1M", ...)` at one position but inserting the corresponding value in `add_row()` at a different position silently misaligns the entire table. Both must be at the same index (position 10, after HV%ile).
- **Not asserting `top_n` passthrough in CLI test** — The key CLI test must verify that `run_pipeline` receives `top_n=20` when `--top-n 20` is passed. Inspect `mock_pipeline.call_args.kwargs['top_n']`.
- **`_make_stock()` helper lacks `perf_1m`** — The display test helper in `test_display.py` doesn't accept `perf_1m`. Either extend it or set `stock.perf_1m = value` directly after creation (the simpler approach matching `test_options_chain.py` pattern).

## Open Risks

- **S01 merge conflicts** — Low probability. S01 touched `pipeline.py` internals (refactored the loop), `market_data.py` (added function at end), and `screened_stock.py` (added one field). None of these overlap with what S02 modifies (`run_screener.py` CLI, `display.py` table columns). Only risk: if `run_screener.py` on S01 branch differs from current, but S01's diff shows no changes to that file.
- **`render_stage_summary` doesn't show top-N cap line** — The filter summary panel shows stock counts at each stage. When `top_n` is active, the count drops between Stage 1 and Earnings due to the cap, but the panel doesn't label this explicitly. Not in requirements — could defer. Users may ask why the gap is unexplained.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | N/A | Standard pattern already in codebase — no specialized skill needed |
| Rich | N/A | `Table.add_column` pattern already established — no skill needed |
| Alpaca | N/A | No Alpaca API changes in S02 |

## Sources

- S01 branch diff (`git diff main..gsd/M002/S01`): 16 files, +924 / -38 lines. Confirmed `perf_1m` field, `compute_monthly_performance()`, `run_pipeline(top_n=)`, and 12 new tests.
- `scripts/run_screener.py` — CLI option patterns and `run_pipeline()` call site (lines 55-126)
- `screener/display.py` — column definitions, row construction, formatter helpers (lines 107-215)
- `tests/test_cli_screener.py` — 5 CLI tests using `CliRunner` + `@patch` stack pattern
- `tests/test_display.py` — 17 display tests with `_make_stock()` helper and `Console(file=StringIO())` capture
- `tests/test_options_chain.py:634-680` — `TestDisplayYieldColumn` as pattern for column-addition tests
- Typer Option signature — confirmed `min` parameter available via introspection
- Test collection: 345 tests pass on current branch
