# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is a low-risk wiring slice. S01 (on branch `gsd/M002/S01`) already implemented the three hard parts: `compute_monthly_performance()` in `screener/market_data.py`, the `perf_1m` field on `ScreenedStock`, and the `top_n` parameter on `run_pipeline()` with sort/cap logic. S02's job is to expose these through the CLI (`--top-n` Typer option) and display (`Perf 1M` column in `render_results_table()`).

All three touch points follow well-established patterns in the codebase. The CLI already has four `typer.Option` parameters with tests via `typer.testing.CliRunner`. The display module already adds columns with `table.add_column()` and formats values with `fmt_pct()`. The existing test files (`test_cli_screener.py`, `test_display.py`) provide clear patterns to follow.

S02 must first merge S01's branch into S02's branch to get the `perf_1m` field and `top_n` parameter.

## Recommendation

1. Merge `gsd/M002/S01` into `gsd/M002/S02` to bring in S01's changes.
2. Add `--top-n` Typer option to `scripts/run_screener.py` — integer, optional, passed through to `run_pipeline(top_n=N)`.
3. Add `Perf 1M` column to `render_results_table()` in `screener/display.py` — positioned after `HV%ile`, before `Yield`, formatted with `fmt_pct()` including sign.
4. Add tests for CLI flag parsing and display column rendering.

All changes are straightforward — no architectural decisions needed, no new libraries, no new patterns.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | `typer.Option` with `Annotated` type hints | Already used for `--verbose`, `--update-symbols`, `--preset`, `--config` |
| CLI testing | `typer.testing.CliRunner` | Already used in `test_cli_screener.py` |
| Table column rendering | `rich.table.Table.add_column()` + `fmt_pct()` | Already used for HV%ile, Yield columns |
| Console capture in tests | `Console(file=StringIO(), width=120)` | Already used in `test_display.py` |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — CLI entry point. All options use `Annotated[type, typer.Option(...)]` pattern. `run_pipeline()` call at line ~95 needs `top_n=top_n` kwarg added.
- `screener/display.py:render_results_table()` — Table has 13 columns currently. `HV%ile` column added in S08 is the closest pattern for adding `Perf 1M`. Uses `fmt_pct()` for percentage values with `"N/A"` fallback for None.
- `screener/display.py:fmt_pct()` — Returns `"X.X%"` format. Does NOT include sign prefix. For `Perf 1M` we need signed display (e.g. `-5.2%`, `+3.1%`). Either add a `fmt_signed_pct()` helper or inline the formatting.
- `tests/test_cli_screener.py` — Tests use `@patch("scripts.run_screener.run_pipeline", ...)` pattern with `runner.invoke(app, [...])`. The `test_screener_help` test checks all option names appear in `--help` output.
- `tests/test_display.py:TestRenderResultsTable` — Tests create `ScreenedStock` objects with `_make_stock()` helper, render to a captured console, and assert column headers and values appear in output.
- `models/screened_stock.py` — `perf_1m: Optional[float] = None` field exists on S01 branch (under `# Technical indicators`). Not on current S02 branch yet — merge required.
- `screener/pipeline.py:run_pipeline()` — `top_n: int | None = None` parameter exists on S01 branch. Not on current S02 branch yet.

## Constraints

- S01 branch (`gsd/M002/S01`) must be merged before S02 can reference `perf_1m` or `top_n`.
- `top_n` must be `Optional[int]` with default `None` — omitting the flag means no cap (TOPN-06 backward compatibility).
- `--top-n` must accept only positive integers. Typer's `int` type handles parsing; validation for `> 0` should be added.
- The `Perf 1M` column should display signed percentages: `-5.2%` for declines, `+3.1%` for gains. The existing `fmt_pct()` doesn't add a `+` sign — need a new formatter or inline format.
- The `render_results_table` column order matters for readability. `Perf 1M` should go near `HV%ile` (both are technical indicators) — after `HV%ile`, before `Yield`.
- The `run_strategy.py` also calls `run_pipeline()` but does NOT need `--top-n` (D042: CLI-only concern). The `run_pipeline()` signature already has `top_n=None` default, so no changes needed there.

## Common Pitfalls

- **Missing S01 merge** — S02 branch is based on main, not S01. Must merge S01 first or the `perf_1m` field and `top_n` parameter won't exist. This is the only prerequisite.
- **`fmt_pct()` doesn't add `+` sign** — Using `fmt_pct()` directly for `Perf 1M` would show `3.1%` instead of `+3.1%`. Need explicit sign formatting for positive values.
- **Forgetting to update `--help` test** — `test_screener_help` checks that all option names appear in help output. Must add `"--top-n"` assertion.
- **Typer `None` default for `int`** — Must use `Optional[int]` (not bare `int`) with `default=None` so the flag is truly optional. The `Annotated[int | None, typer.Option(...)]` pattern is the correct Typer idiom.
- **Negative or zero `top_n`** — Should validate `top_n > 0` in the CLI handler and exit with an error message for invalid values, matching the existing `ValidationError` panel pattern.

## Open Risks

- None significant. All three files to modify (`run_screener.py`, `display.py`, tests) follow established patterns with no ambiguity.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer (CLI) | — | none found (well-documented library, no skill needed) |
| Rich (tables) | — | none found (well-documented library, no skill needed) |

## Sources

- S01 implementation: `git diff main..gsd/M002/S01` — reviewed actual changes to `screener/market_data.py`, `screener/pipeline.py`, `models/screened_stock.py`, `tests/test_pipeline.py`, `tests/test_market_data.py`
- Existing CLI patterns: `scripts/run_screener.py`, `tests/test_cli_screener.py`
- Existing display patterns: `screener/display.py`, `tests/test_display.py`
- Decision register: `.gsd/DECISIONS.md` — D042 (top_n is CLI-only), D044 (None perf_1m sorts last)
