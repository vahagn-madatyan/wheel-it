# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is a low-risk wiring slice: thread the `top_n` parameter from the CLI into the pipeline, and add a "Perf 1M" column to the Rich results table. All heavy lifting (perf computation, sort/cap logic, `perf_1m` field) is done in S01. S02 touches three files — `scripts/run_screener.py` (add Typer option), `screener/display.py` (add column), and their corresponding test files.

The main prerequisite risk is that **S01 exists on branch `gsd/M002/S01` but has not been merged to main**. The current `gsd/M002/S02` branch was created from main and lacks S01's changes. S01 must be merged first (or S02 must be rebased onto S01's branch) before any code changes can work — `run_pipeline` doesn't accept `top_n` and `ScreenedStock` doesn't have `perf_1m` on main.

## Recommendation

1. Merge S01 to main (or rebase S02 onto `gsd/M002/S01`) before implementing.
2. Add `--top-n` as a `typer.Option` with `int | None` type and `None` default — mirrors the existing `--preset` pattern.
3. Pass `top_n` through to `run_pipeline(... top_n=top_n)`.
4. Add "Perf 1M" column to `render_results_table()` using existing `fmt_pct()` helper — slot it between "HV%ile" and "Yield" for logical grouping.
5. Add tests matching established patterns in `test_cli_screener.py` and `test_display.py`.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI argument parsing | Typer `typer.Option` with `Annotated[int \| None, ...]` | Already used for `--preset`, `--verbose`, `--config` |
| Percentage formatting | `screener.display.fmt_pct()` | Handles None → "N/A", consistent format |
| Console capture in tests | `Console(file=StringIO(), width=120)` pattern | Established in `test_display.py` |
| CLI test invocation | `typer.testing.CliRunner` | Established in `test_cli_screener.py` |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — All CLI options use `Annotated[type, typer.Option(...)]` syntax. The `--preset` option demonstrates `Enum | None` with `None` default. `--top-n` follows the same pattern but with `int | None`.
- `scripts/run_screener.py` line calling `run_pipeline()` — Currently passes `trade_client`, `stock_client`, `finnhub`, `cfg`, `on_progress`, `option_client`. Adding `top_n=top_n` is a one-line addition.
- `screener/display.py:render_results_table()` — Columns added via `table.add_column()` then data via `table.add_row()`. Current order: #, Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, HV%ile, Yield, Score, Sector. "Perf 1M" slots naturally between HV%ile and Yield.
- `screener/display.py:fmt_pct()` — Already formats `float | None` → "X.X%" or "N/A". Handles negative values correctly (e.g. "-5.2%"). Perfect for `perf_1m` display.
- `tests/test_cli_screener.py` — Tests use `@patch("scripts.run_screener.<module>")` pattern. Mock `run_pipeline` to verify it receives `top_n` kwarg. Existing test `test_default_no_file_writes` provides a template for default-value verification.
- `tests/test_display.py:_make_stock()` — Helper factory accepts keyword args for each `ScreenedStock` field. Needs `perf_1m` parameter added.
- `tests/test_display.py:TestRenderResultsTable.test_table_has_column_headers()` — Asserts column names in rendered output. Add "Perf 1M" to the list.
- `models/screened_stock.py` (S01 branch) — `perf_1m: Optional[float] = None` field already added by S01.

## Constraints

- **S01 merge required** — `gsd/M002/S01` branch has `run_pipeline(top_n=...)` and `ScreenedStock.perf_1m`. These are not on main. S02 cannot be implemented until S01 is merged or S02 is rebased.
- **Typer integer parsing** — `typer.Option` with `int | None` and default `None` works natively with Typer ≥0.9 (project pins `typer>=0.9.0`). Typer will validate that the value is a positive integer.
- **Column ordering** — The `add_row()` call must match the `add_column()` order exactly. Adding "Perf 1M" requires inserting in both the column definitions and the row data at the same position.
- **No validation needed for top_n=0** — `run_pipeline` handles `top_n=None` (no cap) and `top_n > 0` (cap). Consider adding a Typer `min=1` constraint or letting the pipeline handle it naturally.
- **Backward compatibility (TOPN-06)** — `--top-n` not specified → `None` → pipeline processes all stocks. Default must be `None`, not some number.

## Common Pitfalls

- **Column/row position mismatch** — Adding a column at position N but adding row data at position N+1 will silently shift all subsequent columns. Count carefully and add both column and row data at the same index.
- **Missing `perf_1m` in test helper** — `_make_stock()` in `test_display.py` doesn't accept `perf_1m` yet. Tests will fail unless this helper is updated. Also update `_all_pass_filters()` if perf affects filtering (it doesn't — perf_1m is used for sorting, not filtering).
- **Perf 1M sign display** — `fmt_pct()` already handles negative values (e.g. `-5.2%`) but does NOT add a `+` prefix for positive values. The requirements say "formatted as percentage with sign (e.g. -5.2%, +3.1%)". A new `fmt_signed_pct()` or minor modification may be needed if `+` prefix is desired. Alternatively, accept that `fmt_pct()` output like "3.1%" (no plus) is adequate.
- **Typer hyphenated option name** — `--top-n` in the CLI becomes `top_n` as the Python parameter name. Typer handles this automatically when using `typer.Option("--top-n", ...)`.

## Open Risks

- **S01 not merged** — If S01 merge introduces conflicts or is delayed, S02 is blocked. The S01 summary is a doctor-created placeholder, suggesting possible incomplete documentation, but the code on the branch looks complete (tests for perf computation, sort/cap logic, backward compatibility all present).
- **Positive sign prefix** — TOPN-05 spec says "Formatted as percentage with sign (e.g. -5.2%, +3.1%)". The existing `fmt_pct()` does not add `+` for positive values. This is a minor formatting decision — could use a new helper or accept current behavior. Low risk either way.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer (CLI framework) | — | none found (well-understood, low complexity) |
| Rich (terminal tables) | `autumnsgrove/groveengine@rich-terminal-output` | available (58 installs, not relevant enough — our patterns are established) |

No skills recommended for installation. Both Typer and Rich usage patterns are well-established in the codebase with existing tests to follow.

## Sources

- `scripts/run_screener.py` — existing CLI options pattern (source: codebase)
- `screener/display.py` — column/row rendering pattern (source: codebase)
- `tests/test_cli_screener.py` — CLI test patterns with CliRunner and mocking (source: codebase)
- `tests/test_display.py` — display test patterns with Console capture (source: codebase)
- `gsd/M002/S01` branch — S01 deliverables: `run_pipeline(top_n=)`, `ScreenedStock.perf_1m`, `compute_monthly_performance()` (source: git branch)
