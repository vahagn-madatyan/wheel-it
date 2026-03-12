# S02 ("CLI Flag + Display") — Research

**Date:** 2026-03-11

## Summary

S02 owns three requirements: TOPN-01 (`--top-n` CLI flag), TOPN-05 ("Perf 1M" display column), and TOPN-06 (backward compatibility when flag is omitted). All three are thin integration layers over S01's backend work — a Typer option, a table column, and pass-through wiring. The code changes are small and follow well-established patterns already in the codebase.

**Critical prerequisite:** S01's branch (`gsd/M002/S01`) contains the backend implementation (`perf_1m` field, `compute_monthly_performance()`, `run_pipeline(top_n=)`, sort/cap logic, and 6 pipeline tests) but was **never merged** into the current `gsd/M002/S02` branch. Both branches diverge from the same `main` commit (`cd0624`). S02 must merge or rebase S01 before any of its own work can begin — the `top_n` parameter on `run_pipeline()` and the `perf_1m` field on `ScreenedStock` don't exist on the current branch.

## Recommendation

1. Merge `gsd/M002/S01` into `gsd/M002/S02` first (code changes are clean — only `.gsd/` files may conflict)
2. Add `--top-n` Typer option to `scripts/run_screener.py` following the existing `Annotated[int | None, typer.Option(...)] = None` pattern
3. Pass `top_n=` through to `run_pipeline()` alongside existing `option_client=`
4. Add "Perf 1M" column to `render_results_table()` between "HV%ile" and "Yield", using a signed percentage formatter
5. Add tests for CLI flag parsing, display column, and backward compatibility

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option with None default | Typer `Annotated[int \| None, typer.Option()]` | Already used for `--preset` in same file |
| Percentage formatting | `screener.display.fmt_pct()` | Handles None → "N/A"; needs signed variant for perf |
| Console capture in tests | `Console(file=StringIO(), width=120)` | Established in `test_display.py` |
| CLI invocation tests | `typer.testing.CliRunner` + `@patch` stack | Established in `test_cli_screener.py` |
| Mock stock construction | `_make_stock()` helper in `test_display.py` | Already handles all ScreenedStock fields |

## Existing Code and Patterns

- `scripts/run_screener.py` — Entry point. Options use `Annotated[Type | None, typer.Option("--flag", help="...")]` pattern. Pipeline called as `run_pipeline(broker.trade_client, broker.stock_client, finnhub, cfg, on_progress=..., option_client=...)`. S02 adds `top_n=top_n` kwarg to this call.
- `screener/display.py:render_results_table()` — 13 columns currently. Columns added via `table.add_column(name, ...)` then `table.add_row(...)`. Each field has its own format call (`fmt_price`, `fmt_pct`, `fmt_ratio`, `fmt_large_number`). "Perf 1M" slots between "HV%ile" and "Yield".
- `screener/display.py:fmt_pct()` — Formats `float | None` as `"X.X%"` or `"N/A"`. Does NOT add `+` sign for positive values. S02 needs a `fmt_signed_pct()` or inline `f"{value:+.1f}%"` for the perf column (e.g. `-5.2%`, `+3.1%`).
- `tests/test_cli_screener.py` — 5 tests. CLI test pattern: stack `@patch` decorators for all pipeline dependencies, invoke with `CliRunner`, assert exit code and mock call patterns. The `test_default_no_file_writes` test is the template for a `--top-n` passthrough test.
- `tests/test_display.py` — `_make_stock()` helper creates `ScreenedStock` with specific fields. `_all_pass_filters()` returns passing filter results. `test_table_has_column_headers` asserts column name strings appear in captured output. S02 adds `perf_1m` param to `_make_stock()` and a "Perf 1M" check.
- `screener/display.py:render_stage_summary()` — No changes needed. It counts stocks per stage using filter_results, not columns.

### S01 deliverables on `gsd/M002/S01` branch (not yet on S02 branch)

- `models/screened_stock.py` → `perf_1m: Optional[float] = None` field added after `hv_percentile`
- `screener/market_data.py` → `compute_monthly_performance(bars_df)` — returns `(close[-1] / close[-22] - 1) * 100` or `None` if <22 bars
- `screener/pipeline.py` → `run_pipeline(..., top_n: int | None = None)` — two-pass architecture: Pass 1 runs Stage 1 + populates `perf_1m`; sorts survivors ascending by `perf_1m` (None last); caps to `top_n`; Pass 2 runs Stage 1b/2/3 for capped survivors only
- `tests/test_market_data.py` → 6 tests in `TestComputeMonthlyPerformance`
- `tests/test_pipeline.py` → 5 tests in `TestTopNPipelineCap` (cap behavior, backward compat, sort order, None sorting, perf_1m population)

## Constraints

- **S01 merge required first** — `run_pipeline` does not accept `top_n` and `ScreenedStock` has no `perf_1m` field on the current branch
- Typer 0.24.1 — supports `int | None` union syntax with `Annotated`
- `fmt_pct()` doesn't include `+` sign — need signed formatting for "Perf 1M" column (`-5.2%` vs `+3.1%`)
- Column order matters for visual coherence — "Perf 1M" should go between "HV%ile" (recent vol context) and "Yield" (premium info)
- `_make_stock()` test helper needs `perf_1m` parameter added without breaking existing callers (keyword-only default `None`)
- 345 existing tests must continue passing

## Common Pitfalls

- **S01 merge conflicts on `.gsd/` files** — The S01 branch has `.gsd/STATE.md` and S01 plan/summary/research files that may conflict with S02's `.gsd/` state. Resolve by keeping S02's `.gsd/` state and adding S01's slice artifacts.
- **Typer `--top-n` flag name needs explicit `typer.Option("--top-n")`** — Typer auto-converts `top_n` to `--top-n` for the `Annotated` pattern, but explicit naming is clearer and matches how `--update-symbols` is declared.
- **Forgetting `top_n` in the test mock assertion** — The existing `test_default_no_file_writes` asserts `mock_pipeline.assert_called_once()` without checking kwargs. New test should verify `top_n=N` is in the call kwargs.
- **Positive perf values without `+` sign** — Using plain `fmt_pct()` would show `3.1%` not `+3.1%`. Users need the sign to quickly distinguish gainers from losers in the column.

## Open Risks

- **S01 work integrity** — The S01 summary was a doctor-created placeholder. While the S01 branch diff looks complete and includes proper tests, the actual task summaries were never written. After merging, verify S01's tests pass before building on top.
- **Typer validation of `--top-n 0` or `--top-n -1`** — Typer will parse any integer; pipeline may need a guard for non-positive values. Simple: `if top_n is not None and top_n < 1: typer.Exit(code=1)`.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer CLI | — | none found (standard lib, well-documented) |
| Rich tables | — | none found (standard lib, well-documented) |
| Python options trading | — | none relevant to display/CLI layer |

## Sources

- `gsd/M002/S01` branch diff — S01 implementation details (local git)
- `scripts/run_screener.py` — existing CLI option patterns (local code)
- `tests/test_cli_screener.py` — existing CLI test patterns (local code)
- `tests/test_display.py` — existing display test patterns (local code)
- `screener/display.py` — existing column and formatting patterns (local code)
- Typer docs — `Annotated[int | None, typer.Option()]` pattern (Context7)
