# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 wires the `top_n` pipeline parameter (built in S01) to a `--top-n` CLI flag on `run-screener` and adds a "Perf 1M" column to the Rich results table. This is a thin integration slice — no new algorithmic logic, just plumbing and display.

S01's work lives on branch `gsd/M002/S01` (not yet merged to main). S02 must merge S01 first, then build on top. The S01 diff adds: `perf_1m` field on `ScreenedStock`, `compute_monthly_performance()` in `market_data.py`, `top_n` parameter on `run_pipeline()`, and two-pass pipeline architecture with sort/cap logic. All changes are clean and well-tested (12 new tests).

The three S02 touchpoints are small: ~5 lines in `scripts/run_screener.py` (new Typer option + pass-through + validation), ~5 lines in `screener/display.py` (new column + formatter), and ~50-80 lines of tests.

## Recommendation

1. Merge `gsd/M002/S01` into the S02 working branch first to pick up pipeline changes.
2. Add `--top-n` as `Annotated[int | None, typer.Option(...)]` with in-body validation (`top_n < 1` → error exit). Typer 0.24.1 handles `int | None` natively.
3. Add a signed-percentage formatter (`fmt_signed_pct`) for the Perf 1M column since TOPN-05 requires `+3.1%` format but existing `fmt_pct` produces `3.1%` (no plus sign).
4. Insert "Perf 1M" column in the results table between "HV%ile" and "Yield" — logically groups market data before scoring data.
5. Tests: CLI flag parsing (3-4 tests), display column presence (1-2 tests), formatter (2-3 tests).

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | Typer `Annotated[int \| None, typer.Option()]` | Already used for all other flags; consistent pattern |
| Rich table columns | `table.add_column()` + existing `fmt_pct` pattern | Matches all other columns in `render_results_table` |
| CLI test harness | `typer.testing.CliRunner` | Already used in `test_cli_screener.py` |
| Console capture | `Console(file=StringIO())` | Already used in all display tests |

## Existing Code and Patterns

- **`scripts/run_screener.py:run()`** — All CLI options use `Annotated[T, typer.Option(...)]`. The `--top-n` flag follows this exact pattern. The `results = run_pipeline(...)` call at line ~120 needs `top_n=top_n` added.
- **`screener/display.py:render_results_table()`** — Columns are added sequentially with `table.add_column()`, data formatted inline in the `add_row()` loop. "Perf 1M" inserts between "HV%ile" and "Yield" columns.
- **`screener/display.py:fmt_pct()`** — Formats `X.X%` but without sign prefix. TOPN-05 requires signed format (`-5.2%`, `+3.1%`). Need a new `fmt_signed_pct()` or inline formatting.
- **`tests/test_cli_screener.py`** — Uses `@patch("scripts.run_screener.<module>")` pattern extensively. New `--top-n` tests follow the same mock stack.
- **`tests/test_display.py:_make_stock()`** — Helper builds `ScreenedStock` with arbitrary field values. Needs `perf_1m` parameter added (or set directly on the object).
- **`tests/test_display.py:test_table_has_column_headers()`** — Checks a hardcoded list of column names. Must be updated to include "Perf 1M".
- **S01 pipeline changes** — `run_pipeline()` now accepts `top_n: int | None = None` and `ScreenedStock` has `perf_1m: Optional[float]`. These are the contracts S02 consumes.

## Constraints

- **S01 must be merged first** — `gsd/M002/S01` branch contains `perf_1m` field and `top_n` parameter that S02 depends on. Current S02 branch is based on `main` which lacks these.
- **Typer 0.24.1** — `int | None` with `typer.Option` works. Default `None` means no cap (backward compatible per TOPN-06).
- **Validation must be in-body** — Typer doesn't support custom validators on `Option`. Negative or zero `top_n` needs a manual check → `Console(stderr=True)` + `typer.Exit(code=1)`, matching the existing `ValidationError` error pattern.
- **Column ordering** — Rich tables are ordered by `add_column()` call sequence. "Perf 1M" must be inserted at the right position in the existing sequence.
- **Existing `test_table_has_column_headers` test** — Asserts a hardcoded column list. Adding "Perf 1M" column requires updating this test, otherwise it'll pass vacuously (only checks listed columns exist, doesn't fail on extras) but won't verify the new column.

## Common Pitfalls

- **Forgetting to pass `top_n` through to `run_pipeline()`** — The Typer option must be threaded into the `run_pipeline(...)` call. Easy to add the flag but forget the pass-through.
- **Not merging S01 first** — Without `perf_1m` on `ScreenedStock` and `top_n` on `run_pipeline()`, the CLI flag and display column have nothing to connect to. Tests will fail at import time.
- **`fmt_pct` vs signed format** — Using the existing `fmt_pct()` for Perf 1M would produce `3.1%` instead of the required `+3.1%`. Need explicit sign handling.
- **Typer `int | None` edge case** — User passing `--top-n 0` would be parsed as `0` (valid int), not `None`. Body validation must catch `top_n <= 0`.

## Open Risks

- **S01 merge conflicts** — S01 modifies `pipeline.py`, `market_data.py`, `screened_stock.py`, and test files. The S02 branch has no code changes yet, so merge should be clean. Verify after merge.
- **Existing test count regression** — Currently 345 tests on main. S01 adds 12. After merge, 357 must pass before S02 starts adding its own.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer CLI | No directly relevant skill | none found |
| Rich (Python) | No directly relevant skill | none found |

## Sources

- Codebase exploration: `scripts/run_screener.py`, `screener/display.py`, `models/screened_stock.py`, `screener/pipeline.py`, `tests/test_cli_screener.py`, `tests/test_display.py`
- S01 branch diff: `git diff main..gsd/M002/S01`
- Typer 0.24.1 `int | None` behavior: verified via interactive test
