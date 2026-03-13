# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 is a low-risk wiring slice that connects S01's `run_pipeline(top_n=N)` parameter to a `--top-n` Typer CLI option and adds a "Perf 1M" column to the Rich results table. All the hard work (two-pass pipeline refactor, sort/cap logic, `compute_monthly_performance()`, `perf_1m` field) was done in S01 on branch `gsd/M002/S01`. S02's job is strictly surface-level: one new CLI parameter, one new table column, and tests for both.

The S01 branch must be merged into `gsd/M002/S02` before any implementation begins — the source files on the current branch do not yet have `perf_1m`, `compute_monthly_performance()`, or `top_n` changes. The merge should be clean since S02's branch has no conflicting source code changes.

The existing codebase has strong established patterns for both changes: Typer option patterns in `scripts/run_screener.py` (4 existing `Annotated[..., typer.Option()]` params), display column patterns in `screener/display.py` (`render_results_table()` with 12 columns, `fmt_pct()` helper already exists), and comprehensive test patterns in `tests/test_display.py` (45 tests) and `tests/test_call_screener.py` (Typer CliRunner tests).

## Recommendation

Two tasks:

1. **T01 — CLI flag**: Add `--top-n` option to `scripts/run_screener.py`, thread it into `run_pipeline(top_n=N)`. Test with `CliRunner` for flag parsing, `None` default, and value forwarding. Follow the existing `PresetName` / `Annotated` pattern.

2. **T02 — Display column**: Add "Perf 1M" column to `render_results_table()` using existing `fmt_pct()` helper with sign prefix. Add tests verifying column presence and formatting. The `_make_stock` helper in tests needs a `perf_1m` kwarg added.

Both tasks are independent and could be parallelized, but sequential is fine given the low complexity (~20 LOC each).

**Pre-task 0**: Merge `gsd/M002/S01` into current branch before any code changes.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option declaration | Typer `Annotated[..., typer.Option()]` pattern | 4 existing options in `run_screener.py` use this exact pattern |
| Percentage formatting | `screener.display.fmt_pct()` | Already handles None→"N/A" and `{value:.1f}%` formatting |
| CLI testing | `typer.testing.CliRunner` | Used in `test_call_screener.py` — proven pattern for testing Typer apps |
| Console capture in tests | `Console(file=StringIO(), width=120)` helper | `_capture_console()` helper already exists in `test_display.py` |

## Existing Code and Patterns

- `scripts/run_screener.py:56-73` — Four `Annotated[..., typer.Option()]` params. New `--top-n` follows same pattern: `Annotated[int | None, typer.Option("--top-n", help="...")]` with default `None`.
- `scripts/run_screener.py:119-126` — `run_pipeline()` call site. Add `top_n=top_n` kwarg here.
- `screener/display.py:163-228` — `render_results_table()`. Add column with `table.add_column("Perf 1M", justify="right")` and `add_row()` gets a `fmt_pct(stock.perf_1m)` value. Must add sign prefix — `fmt_pct` currently does not include `+` for positive values.
- `screener/display.py:105-110` — `fmt_pct()` returns `f"{value:.1f}%"` for non-None. For Perf 1M, a sign-aware variant is needed: `f"{value:+.1f}%"` (Python format spec with `+` flag). Could use a new helper `fmt_signed_pct()` or add a `signed` parameter to `fmt_pct`.
- `tests/test_display.py:30-58` — `_make_stock()` helper and `_all_pass_filters()`. Add `perf_1m` parameter to `_make_stock()`.
- `tests/test_call_screener.py:642-700` — CliRunner pattern with `@patch` decorators on module-level imports. Follow this for CLI tests.
- `models/screened_stock.py:42` (on S01 branch) — `perf_1m: Optional[float] = None` field, placed after `hv_percentile`.

## Constraints

- **S01 merge required**: `gsd/M002/S01` branch must be merged first — it contains `perf_1m` field, `compute_monthly_performance()`, and `run_pipeline(top_n=...)` changes.
- **Column position**: "Perf 1M" should go near other market-data columns. Logical placement is after "HV%ile" and before "Yield" — that groups performance metrics together.
- **Sign display**: TOPN-05 specifies format like `-5.2%` and `+3.1%`. Python's `f"{value:+.1f}%"` format spec handles this natively (positive gets `+`, negative gets `-`).
- **Backward compatibility (TOPN-06)**: When `--top-n` is omitted, `top_n=None` flows to `run_pipeline()` which processes all stocks. No default cap value.
- **Typer 0.24.1**: Confirmed `int | None` type annotation works correctly — tested live with `CliRunner`.

## Common Pitfalls

- **Forgetting to pass `top_n` to `run_pipeline()`** — The Typer option exists but is never threaded through. Verify with a test that mocks `run_pipeline` and checks the `top_n` kwarg.
- **`fmt_pct` doesn't show `+` sign** — The existing `fmt_pct` returns `5.2%` not `+5.2%`. Either add a `signed` param or use a new `fmt_signed_pct()` helper. Tests must check both positive and negative formatting.
- **Test helper `_make_stock` missing `perf_1m`** — The display test helper doesn't accept `perf_1m` yet. Forgetting to add it means test stocks will always have `perf_1m=None`, making column output "N/A" for all rows.
- **Stale `.pyc` cache after merge** — After merging S01, pycache may mask problems. Run `find . -name '*.pyc' -delete` after merge.

## Open Risks

- **S01 merge conflict risk is near-zero** — S02 branch has only `.gsd/` file changes; S01 branch modifies `models/screened_stock.py`, `screener/market_data.py`, `screener/pipeline.py`, and `tests/`. No overlap in source files.
- **No validation on `top_n` value** — Typer handles `int` parsing, but negative values or zero could be passed. Low risk: `run_pipeline()` would just return all stocks with `top_n=0` (empty slice) or negative (no-op). Could add `typer.Option(min=1)` or a Typer callback for safety.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | — | none found (core Python library, well-documented, patterns already established in codebase) |
| Rich | — | none found (core Python library, patterns already established in codebase) |

No external skills are needed — both technologies are standard Python libraries with extensive in-project usage patterns.

## Sources

- S01 branch `gsd/M002/S01` — diff reviewed for exact API surface (`perf_1m` field, `run_pipeline(top_n=...)`, `compute_monthly_performance()`)
- S01 task summaries `T01-SUMMARY.md` and `T02-SUMMARY.md` — confirmed 357 tests passing, two-pass architecture, sort/cap behavior
- Existing `scripts/run_screener.py` — Typer option pattern with `Annotated[..., typer.Option()]`
- Existing `tests/test_call_screener.py` — CliRunner test pattern with `@patch` decorators
- Existing `tests/test_display.py` — 45 display tests with `_make_stock` helper and `_capture_console`
- Live Typer 0.24.1 test — confirmed `int | None` annotation works for optional integer flags
