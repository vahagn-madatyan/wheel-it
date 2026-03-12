# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is a low-risk wiring slice. S01 (on branch `gsd/M002/S01`, not yet merged to current branch) already delivers all the hard work: `compute_monthly_performance()`, `perf_1m` field on `ScreenedStock`, the two-pass pipeline architecture with `run_pipeline(top_n=N)`, sort/cap logic, and 12 new tests (6 math + 6 pipeline). S02 must merge S01's code first, then add three things: a `--top-n` Typer option in `scripts/run_screener.py` that passes through to `run_pipeline(top_n=N)`, a "Perf 1M" column in `screener/display.py:render_results_table()`, and tests for both.

All three target files have clear, established patterns. The CLI file uses `typer.Option` with `Annotated` type hints. The display file uses `fmt_pct()` for percentage columns and follows a consistent `table.add_column()` + `table.add_row()` pattern. The test files use `typer.testing.CliRunner` for CLI tests and `Console(file=StringIO())` capture for display tests. No new libraries, no new patterns, no API calls.

## Recommendation

1. **Merge S01 branch first** — `git merge gsd/M002/S01` into the S02 branch to get `perf_1m`, `compute_monthly_performance()`, `run_pipeline(top_n=)`, and all S01 tests.
2. **Add `--top-n` CLI option** — A single `typer.Option` in `run()` with `int | None` type, passed to `run_pipeline(top_n=top_n)`. Follows the exact same pattern as `--verbose`, `--preset`, etc.
3. **Add "Perf 1M" column** — Insert between "HV%ile" and "Yield" in `render_results_table()`. Use existing `fmt_pct()` with sign formatting (e.g. `+3.1%`, `-5.2%`). Note: `fmt_pct()` already handles negatives correctly but doesn't prefix `+` for positives — needs a small `fmt_perf()` helper or inline sign logic.
4. **Tests** — CLI: verify `--top-n` is passed through to `run_pipeline()`. Display: verify "Perf 1M" column appears, handles None, shows sign.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | `typer.Option` with `Annotated` | Already used for `--verbose`, `--preset`, `--config`, `--update-symbols` |
| Table rendering | `rich.table.Table` | Already used in `render_results_table()` |
| Percentage formatting | `fmt_pct()` in `screener/display.py` | Already handles None → "N/A" and negative values |
| CLI testing | `typer.testing.CliRunner` | Already used in `tests/test_cli_screener.py` |
| Console capture | `Console(file=StringIO())` | Already used in `tests/test_display.py` |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — CLI entry point. Uses `Annotated[type, typer.Option()]` pattern for all options. `run_pipeline()` call at line 119 needs `top_n=top_n` kwarg added. Already imports everything needed except the new option.
- `screener/display.py:render_results_table()` — Table builder. Columns added with `table.add_column()`, rows with `table.add_row()`. "HV%ile" column at position 10, "Yield" at 11, "Score" at 12. Insert "Perf 1M" between HV%ile and Yield (or after Yield, before Score).
- `screener/display.py:fmt_pct()` — Formats `float | None` as `"X.X%"` / `"N/A"`. Does not add `+` prefix for positive values. S02 needs `+` prefix for perf to distinguish gains from losses visually — either a new `fmt_signed_pct()` or inline logic.
- `tests/test_cli_screener.py` — 5 CLI tests using `CliRunner` + `@patch`. Pattern: patch all external dependencies at module level (`scripts.run_screener.X`), invoke with `runner.invoke(app, [...])`, assert exit code and mock calls.
- `tests/test_display.py` — 35 tests. `_make_stock()` helper and `_all_pass_filters()` factory. `_capture_console()` returns `Console(file=StringIO(), width=120)`. Test pattern: render to captured console, check `console.file.getvalue()` for expected strings.
- `models/screened_stock.py` — `perf_1m: Optional[float] = None` already added by S01 (on branch). Located in Technical indicators section after `hv_percentile`.
- `screener/pipeline.py:run_pipeline()` — `top_n: int | None = None` parameter already added by S01. Sort/cap logic already implemented.

## Constraints

- **S01 must be merged first** — `perf_1m` field, `compute_monthly_performance()`, and `run_pipeline(top_n=)` all live on branch `gsd/M002/S01`. Without merging, S02 code has nothing to wire to.
- **`top_n` must be `None` by default** — D042 and TOPN-06 require backward compatibility. When omitted, all stocks process through full pipeline.
- **`top_n` must be a positive integer** — Typer's `int` type handles basic parsing. Consider adding `min=1` validation or letting pipeline handle `top_n=0` gracefully.
- **Column insertion order matters** — Rich table column order is positional. Adding "Perf 1M" means updating existing test assertions that check column presence (but current tests only check column names exist in output, not order, so this is safe).
- **345 existing tests must pass** — S01 brought it to 357 (345 + 12 new). S02 adds more. All must pass.

## Common Pitfalls

- **Forgetting to merge S01** — The current branch (`gsd/M002/S02`) does not have `perf_1m`, `top_n`, or `compute_monthly_performance()`. Must merge `gsd/M002/S01` before coding.
- **`fmt_pct()` doesn't show `+` sign** — Using `fmt_pct()` directly for perf_1m will show `3.1%` for positive and `-3.1%` for negative. For clarity, positive values should show `+3.1%`. Need either a wrapper or format string like `f"{value:+.1f}%"`.
- **Patching `run_pipeline` in CLI tests** — Must patch at `scripts.run_screener.run_pipeline`, not `screener.pipeline.run_pipeline` (per D019 pattern — module-level imports in CLI entry points).
- **`_make_stock()` helper doesn't set `perf_1m`** — The `_make_stock()` helper in `tests/test_display.py` needs a `perf_1m` parameter added, or tests should set it directly on the returned stock object.

## Open Risks

- **S01 merge conflicts** — S01 modifies `screener/pipeline.py`, `models/screened_stock.py`, `screener/market_data.py`, and `tests/test_pipeline.py`. The current S02 branch was created from the same base, so merge should be clean, but verify.
- **`top_n=0` edge case** — If user passes `--top-n 0`, pipeline would cap to 0 stocks (empty results). Consider whether Typer should validate `min=1` or if pipeline should treat 0 as "no cap". Low risk — user error, not a functional bug.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer CLI | (none relevant) | none found |
| Rich tables | `autumnsgrove/groveengine@rich-terminal-output` | available (58 installs) — not relevant enough for this simple column addition |

## Sources

- S01 branch diff (`git diff main..gsd/M002/S01`) — confirmed all S01 deliverables exist: `perf_1m` field, `compute_monthly_performance()`, `run_pipeline(top_n=)`, 12 tests
- S01 task summaries (T01-SUMMARY.md, T02-SUMMARY.md on S01 branch) — confirmed verification passed, 357 total tests
- Existing code: `scripts/run_screener.py`, `screener/display.py`, `tests/test_cli_screener.py`, `tests/test_display.py` — confirmed patterns for CLI options, table columns, and test approaches
