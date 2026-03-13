# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 wires S01's deliverables to the user surface: a `--top-n` CLI flag on `run-screener` and a "Perf 1M" column in the results table. All computation and pipeline logic already exists on the `gsd/M002/S01` branch (verified: 357 tests pass including 12 new ones for perf computation, sort/cap, and two-pass pipeline). S02 touches three production files and two test files, all following heavily established patterns.

The critical prerequisite is merging `gsd/M002/S01` into `gsd/M002/S02` — the S02 branch currently lacks the `perf_1m` field, `compute_monthly_performance()`, and `top_n` parameter on `run_pipeline()`. The merge should be clean: S02 has zero `.py` diffs from `main`, only `.gsd/` changes.

S02 owns three requirements: TOPN-01 (CLI flag), TOPN-05 (display column), TOPN-06 (backward compatibility). All are straightforward — each requires ~10 lines of production code following existing patterns already proven across 345+ tests.

## Recommendation

**Merge S01 first, then implement two small tasks:**

1. **CLI flag (TOPN-01, TOPN-06):** Add `--top-n` as an `Annotated[int | None, typer.Option()]` to `run()` in `scripts/run_screener.py`. Pass it through to `run_pipeline(top_n=top_n)`. Default is `None` (no cap — backward compatible). Test via `CliRunner` following the `test_default_no_file_writes` and `test_verbose_shows_filter_breakdown` patterns.

2. **Display column (TOPN-05):** Add "Perf 1M" column to `render_results_table()` in `screener/display.py` between "HV%ile" and "Yield". Use a signed percentage formatter (`f"{value:+.1f}%"`) since direction matters for performance values — distinct from `fmt_pct()` which is used for RSI/margins where `+` sign would be misleading.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | `Annotated[T, typer.Option()]` pattern | Used 4 times already in `run_screener.py:run()` (lines 57–73) |
| CLI testing | `typer.testing.CliRunner` + `@patch` | Used in 5 tests in `test_cli_screener.py` |
| Rich table columns | `table.add_column()` + `table.add_row()` | 13 columns already in `render_results_table()` |
| Percentage formatting | `fmt_pct()` for unsigned; `f"{v:+.1f}%"` for signed | `fmt_pct` handles None→"N/A"; signed format needs a small helper |
| Console capture for tests | `Console(file=StringIO(), width=120)` via `_capture_console()` | Used in all `test_display.py` tests |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — Typer command with 4 `Annotated` options (lines 57–73). The `--top-n` option slots in identically. The `run_pipeline()` call (line 119) gains `top_n=top_n`. No new imports needed.
- `screener/display.py:render_results_table()` — 13 columns (#, Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, HV%ile, Yield, Score, Sector). "Perf 1M" inserts between "HV%ile" (line 190) and "Yield" (line 191). The `add_row()` call (line 202) needs a matching new value.
- `screener/display.py:fmt_pct()` — Formats `float | None → "X.X%" | "N/A"`. Does NOT add `+` prefix for positive values. For perf_1m where sign matters, use a dedicated `fmt_signed_pct()` helper: `f"{value:+.1f}%"` for `float`, `"N/A"` for `None`.
- `tests/test_cli_screener.py:test_default_no_file_writes()` — Gold pattern: 8 `@patch` decorators, `CliRunner.invoke(app, [])`, assert `run_pipeline` called with expected args. Clone for `--top-n 20` test.
- `tests/test_display.py:_make_stock()` — Helper that builds `ScreenedStock` with optional kwargs. Doesn't currently accept `perf_1m` — set it directly via `stock.perf_1m = X` (dataclass allows attribute assignment).
- `tests/test_display.py:TestRenderResultsTable` — 7 existing tests. Add test for "Perf 1M" column presence, positive/negative formatting, and None→"N/A".

### S01 Deliverables (verified on `gsd/M002/S01` branch, 357 tests pass)

- `models/screened_stock.py` — `perf_1m: Optional[float] = None` field after `hv_percentile`
- `screener/market_data.py` — `compute_monthly_performance(bars_df) → float | None` (22-bar lookback, returns percentage)
- `screener/pipeline.py` — `run_pipeline(..., top_n: int | None = None)` parameter; two-pass architecture splits Stage 1 from Stage 1b/2/3 with sort/cap in between. Sort key: `perf_1m if not None else inf` (ascending — worst performers first, None last).
- `tests/test_market_data.py` — 6 new tests in `TestComputeMonthlyPerformance` (exact 22 bars, 250 bars, insufficient data, negative/positive/flat returns)
- `tests/test_pipeline.py` — 6 new tests in `TestTopNPipelineCap` (caps stage2 calls, None→all, ascending sort, None sorts last, perf populated, all stocks returned)

## Constraints

- **Merge S01 first:** S02 branch has zero `.py` changes from `main`. S01 modifies 5 `.py` files (407 insertions). Merge should be conflict-free.
- **`top_n` type: `int | None`** — Must not default to `0` or any integer. `None` = no cap (TOPN-06/D042). Typer handles `Optional[int]` correctly with `default=None`.
- **`run_strategy.py` is untouched** — It calls `run_pipeline()` without `top_n` or `option_client`. The new `top_n=None` default preserves this.
- **Signed percentage for Perf 1M** — TOPN-05 says "percentage with sign (e.g. -5.2%, +3.1%)". The `fmt_pct()` function does NOT add `+`. Create `fmt_signed_pct()` or inline `f"{v:+.1f}%"` — avoids polluting `fmt_pct` which is used for RSI/margins/growth where `+` prefix would be wrong.
- **Column position** — Insert after "HV%ile" (line 190), before "Yield" (line 191). Both `add_column()` and `add_row()` must match order.
- **D019 (module-level imports)** — CLI imports must be at module level for `@patch` to work. No new imports needed for `--top-n`.
- **`test_table_has_column_headers`** — Existing test checks column names by substring match in rendered output. Adding "Perf 1M" won't break it, but the new test should explicitly verify "Perf 1M" presence.

## Common Pitfalls

- **Forgetting to merge S01** — Implementation will `AttributeError` immediately if `perf_1m` field or `top_n` parameter don't exist. Merge first, run `pytest`, verify 357 pass.
- **`add_column` / `add_row` order mismatch** — Rich tables map columns to row values positionally. If "Perf 1M" column is added at position 11 but the `add_row()` value is at position 12, all subsequent columns shift. Count carefully: 14 columns after addition.
- **Typer `int | None` union** — Python 3.13 supports `int | None` in annotations. Typer 0.24.1 handles this correctly. Don't accidentally use `Optional[int] = 0`.
- **Positive perf without `+` sign** — If `fmt_pct(3.1)` → `"3.1%"`, users won't know if that's positive or flat. Use signed format for perf specifically.
- **Existing tests sensitive to column count** — `test_table_has_column_headers` checks specific strings, not column count. `test_table_row_count` checks symbol presence. Neither should break. But review after implementation.

## Open Risks

- **S01 merge conflicts** — Low risk: S02 has zero `.py` diffs from `main`. Only `.gsd/` metadata files differ, which merge independently. Verified via `git diff gsd/M002/S02..gsd/M002/S01 --stat -- '*.py'` showing clean diff.
- **`fmt_signed_pct` testing** — New helper needs its own unit tests (positive→"+3.1%", negative→"-5.2%", zero→"+0.0%", None→"N/A"). Small scope but don't skip it.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer CLI | — | installed patterns sufficient (4 existing `Annotated` options in same file) |
| Rich tables | — | installed patterns sufficient (13-column table already in `display.py`) |

No external skills needed — all patterns are thoroughly established in the existing codebase.

## Sources

- `gsd/M002/S01` branch — verified via `git diff` and `pytest` (357 tests pass, 12 new)
- `scripts/run_screener.py` — current CLI implementation (4 Typer options, `run_pipeline` call at line 119)
- `screener/display.py` — current 13-column results table (lines 172–215)
- `tests/test_cli_screener.py` — 5 CLI tests with `CliRunner` + `@patch` pattern
- `tests/test_display.py` — 30+ display tests with `_make_stock()` / `_capture_console()` helpers
