# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 is a low-risk wiring slice that connects S01's pipeline internals to user-visible surfaces: a `--top-n` CLI flag on `run-screener` and a "Perf 1M" column in the Rich results table. All heavy lifting (perf computation, sort/cap logic, two-pass pipeline) lives in S01 on branch `gsd/M002/S01` and must be merged before S02 work begins.

The implementation touches exactly three files (`scripts/run_screener.py`, `screener/display.py`, `tests/`) with well-established patterns to follow. Both the CLI and display changes are additive — no existing behavior changes.

The primary nuance is formatting: the requirements spec "Perf 1M" values with explicit sign (`-5.2%`, `+3.1%`), but the existing `fmt_pct()` only shows sign for negative values. A small formatting helper or inline format string handles this.

## Recommendation

1. **Merge S01 branch first** — `git merge gsd/M002/S01` into `gsd/M002/S02` to get `perf_1m` field, `compute_monthly_performance()`, and `run_pipeline(top_n=)` parameter.
2. **Add `--top-n` CLI option** — Follow the existing `Annotated[..., typer.Option(...)]` pattern. Pass through to `run_pipeline(top_n=top_n)`.
3. **Add "Perf 1M" column** — Insert between "HV%ile" and "Yield" in `render_results_table()`. Use a signed-percent formatter.
4. **Test both surfaces** — CLI flag test via `typer.testing.CliRunner`; display column test via `Console(file=StringIO())` capture.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | `typer.Option` with `Annotated` type hints | Already used for `--verbose`, `--preset`, `--config` — consistent pattern |
| Table rendering | `rich.table.Table` with `add_column` / `add_row` | Already used for 13 columns in `render_results_table()` |
| Number formatting | `fmt_pct()` in `screener/display.py` | Handles None → "N/A" and `%.1f%` formatting; extend for sign |
| CLI testing | `typer.testing.CliRunner` | Used in all 5 existing CLI tests in `test_cli_screener.py` |
| Display testing | `Console(file=StringIO(), width=120)` capture | Used in all 17 existing display tests in `test_display.py` |

## Existing Code and Patterns

- `scripts/run_screener.py:55-73` — CLI option pattern: `Annotated[type | None, typer.Option("--flag", help="...")]`. S02's `--top-n` follows this exactly.
- `scripts/run_screener.py:119-126` — `run_pipeline()` call site. S02 adds `top_n=top_n` kwarg here.
- `screener/display.py:181-193` — Column definitions. S02 inserts "Perf 1M" column after "HV%ile" (line 190) and before "Yield" (line 191).
- `screener/display.py:195-215` — Row construction. S02 adds `perf_1m` formatting in the `add_row()` call at corresponding position.
- `screener/display.py:107-118` — `fmt_pct()` — Returns `f"{value:.1f}%"` or `"N/A"`. Doesn't add `+` for positive values. S02 needs a signed variant.
- `tests/test_cli_screener.py:36-74` — `test_default_no_file_writes` — canonical CLI test pattern: patch all dependencies, invoke via runner, assert calls. S02's `--top-n` test follows this.
- `tests/test_display.py:64-78` — `_make_stock()` helper — creates `ScreenedStock` with specified fields. S02 adds `perf_1m` kwarg.
- `tests/test_display.py:80-88` — `_all_pass_filters()` — returns passing filter results. Reuse as-is.
- `models/screened_stock.py` — `ScreenedStock` dataclass. S01 adds `perf_1m: Optional[float] = None` after `hv_percentile`. S02 consumes this field in display.

## Constraints

- **S01 must be merged first.** S02 depends on `ScreenedStock.perf_1m`, `compute_monthly_performance()`, and `run_pipeline(top_n=)` — all live on branch `gsd/M002/S01`.
- **`top_n` must be `int | None`, default `None`.** Per D042, `None` means no cap (backward compatible, TOPN-06). Typer handles `int | None` natively.
- **`top_n` must be a positive integer when set.** Typer's `min=1` constraint or a manual check. Zero or negative values are nonsensical.
- **Column order matters.** "Perf 1M" logically belongs between technical indicators (HV%ile) and options data (Yield) — after HV%ile, before Yield.
- **Perf 1M format requires explicit sign.** Requirements say `-5.2%`, `+3.1%` — positive values need `+` prefix, not just bare number (TOPN-05).
- **345 existing tests must still pass.** S02 changes are additive, no existing signatures change.

## Common Pitfalls

- **Forgetting to merge S01 first** — `perf_1m` field doesn't exist on current branch; tests and display code will fail to compile. Merge `gsd/M002/S01` as the first task.
- **Using `fmt_pct()` directly for signed display** — `fmt_pct(-5.2)` returns `"-5.2%"` (correct), but `fmt_pct(3.1)` returns `"3.1%"` (missing `+`). Need either a new `fmt_pct_signed()` or inline `f"{value:+.1f}%"`.
- **Not validating `top_n >= 1`** — Typer allows `--top-n 0` or `--top-n -1` without explicit constraint. Add `min=1` to the `typer.Option` or validate manually.
- **Column/row position mismatch** — Adding a column to `add_column()` without adding the corresponding value in the `add_row()` call (or at wrong position) silently misaligns the table. Count carefully: "Perf 1M" should be column position 11 (after HV%ile at 10, before Yield at current 11 which shifts to 12).
- **Patching `run_pipeline` without `top_n` kwarg check** — CLI tests should assert that `run_pipeline` receives `top_n=N` when `--top-n N` is passed. Use `mock_pipeline.assert_called_once()` then inspect `call_args.kwargs['top_n']`.

## Open Risks

- **S01 merge conflicts** — If S01 modified lines near the `run_pipeline()` call in `run_screener.py` or column definitions in `display.py`, merge may have conflicts. Low probability: S01 only touched `pipeline.py`, `market_data.py`, and `screened_stock.py` internals.
- **`render_stage_summary` may benefit from a "Top-N cap" line** — The stage summary panel shows stock counts at each stage. When top_n is active, the count drops between Stage 1 and Stage 1b due to the cap, but the current summary doesn't label this. Consider whether to add a "Top-N cap" line. Not in requirements — could defer.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | N/A | No specialized skill needed — standard pattern already in codebase |
| Rich | N/A | No specialized skill needed — `Table.add_column` pattern established |
| Python | N/A | Core language features only |

## Sources

- S01 diff via `git diff gsd/M002/S02..gsd/M002/S01` — confirmed S01 adds `perf_1m` field, `compute_monthly_performance()`, `top_n` parameter, and 12 new tests
- `scripts/run_screener.py` — existing CLI option patterns (lines 55-73)
- `screener/display.py` — existing column/formatting patterns (lines 107-215)
- `tests/test_cli_screener.py` — existing CLI test patterns (5 tests, CliRunner-based)
- `tests/test_display.py` — existing display test patterns (17 tests, Console capture)
- 345 existing tests confirmed via `pytest --co -q`
