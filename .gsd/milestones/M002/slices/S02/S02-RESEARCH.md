# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 wires two remaining user-facing pieces for the top-N feature: a `--top-n` CLI flag on `run-screener` and a "Perf 1M" column in the Rich results table. Both are straightforward additions that follow well-established patterns already in the codebase.

The biggest risk is the **dependency on S01**, which is supposed to deliver `ScreenedStock.perf_1m`, perf computation in `compute_indicators()`, and `run_pipeline(top_n=N)`. The roadmap marks S01 as complete, but STATE.md shows it still in "planning" and none of its deliverables exist in code — no `perf_1m` field, no `top_n` parameter, no monthly perf computation. **S02 cannot be executed until S01 is truly complete.**

Assuming S01 delivers as specified, S02 is a low-risk slice — ~2 tasks touching 3 files with clear precedent for every change.

## Recommendation

Wait for S01 to actually deliver its boundary outputs, then implement S02 in two tasks:

1. **CLI flag** — Add `--top-n` Typer option to `scripts/run_screener.py`, pass through to `run_pipeline(top_n=N)`. Follow the exact same `Annotated[type, typer.Option()]` pattern used by the 4 existing options (`--update-symbols`, `--verbose`, `--preset`, `--config`). Use Typer's native `min=1` constraint (confirmed available in Typer 0.24.1). Test with `CliRunner` mocking `run_pipeline`.

2. **Display column** — Add "Perf 1M" column to `render_results_table()` in `screener/display.py`. Add a `fmt_signed_pct()` formatter since TOPN-05 requires sign prefixes (`+3.1%`, `-5.2%`) and the existing `fmt_pct()` omits the `+` for positive values. Position the column near HV%ile/Yield (before Score). Test with `Console(file=StringIO())` capture pattern.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | Typer `typer.Option(min=1)` | Already used for 4 options in `run_screener.py`; provides help text, type validation, min constraint |
| Table column rendering | Rich `Table.add_column()` + `Table.add_row()` | Already used for 12 columns in `render_results_table()` |
| Percentage formatting | `fmt_pct()` in `screener/display.py` | Handles None→"N/A"; need a signed variant for perf column |
| CLI testing | `typer.testing.CliRunner` | Already used in `test_cli_screener.py` with well-established mock patterns |
| Display testing | `Console(file=StringIO(), width=N)` | Already used in `test_display.py` and `test_options_chain.py` |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — CLI entry point. All 4 existing options use `Annotated[type, typer.Option(...)]`. The `--top-n` flag adds a 5th option: `Optional[int]` with default `None`. Pass to `run_pipeline(top_n=top_n)`.
- `screener/display.py:render_results_table()` — Builds a Rich Table with 12 columns. "Perf 1M" inserts as column 11 (before Score). The yield column added in S09 is the most recent precedent for adding a column.
- `screener/display.py:fmt_pct()` — Formats `float|None → "X.X%"|"N/A"`. Does NOT add `+` prefix for positive values. Need a `fmt_signed_pct()` for the Perf 1M column (TOPN-05 requires `+3.1%`, `-5.2%`).
- `tests/test_cli_screener.py` — 4 CLI tests using `CliRunner` with extensive `@patch` decorators (8 patches per test). The `test_verbose_shows_filter_breakdown` test is the closest pattern for testing a new flag: patches pipeline + display, invokes with flag, asserts specific function called with expected args. The `test_screener_help` test asserts all option names appear in help output — must add `--top-n`.
- `tests/test_display.py` — `_make_stock()` helper (positional-kwarg style, needs `perf_1m` kwarg added), `_all_pass_filters()`, `_capture_console()` — reusable test fixtures. `test_table_has_column_headers` pattern: render table, assert column header strings exist in output.
- `tests/test_options_chain.py:test_yield_column_in_results_table()` — Most recent column addition test. Creates stock via `_make_stock(**kwargs)` (different helper — uses `setattr`), renders table to `Console(file=buf, width=200)`, asserts column header + formatted value in output. Follow this pattern for the Perf 1M column test.
- `screener/pipeline.py:run_pipeline()` — S01 should add `top_n=None` parameter. S02 passes the CLI value through. No pipeline logic changes in S02.
- `models/screened_stock.py:ScreenedStock` — S01 should add `perf_1m: Optional[float] = None`. S02 reads this field in display.

## Constraints

- **S01 must be complete first** — S02 consumes `ScreenedStock.perf_1m` and `run_pipeline(top_n=N)`, neither of which exist yet.
- `top_n` must be `Optional[int]` defaulting to `None` — backward compatible per TOPN-06.
- `top_n` must be a positive integer when provided — Typer 0.24.1 natively supports `min=1` on `typer.Option()`.
- `fmt_pct()` cannot be modified to always show sign — it's used by Margin, Growth, RSI, HV%ile, and Yield columns where `+` prefix is unwanted. Need a separate formatter.
- The display column order matters — "Perf 1M" should appear near HV%ile/Yield since it's a performance metric, logically before Score.
- `_make_stock()` helper in `test_display.py` is positional-kwarg style and does NOT have `hv_percentile` or `put_premium_yield` kwargs — must add `perf_1m` kwarg. The `test_options_chain.py` helper uses `setattr(**kwargs)` pattern which is more flexible.
- 345 existing tests must continue passing.

## Common Pitfalls

- **Changing `fmt_pct` to show sign globally** — Would break 5+ existing column formats. Use a separate `fmt_signed_pct()` that adds `+` for positive values.
- **Not validating top_n >= 1** — `--top-n 0` or `--top-n -5` would silently produce empty results. Use Typer's `min=1` constraint.
- **Forgetting to pass top_n through to `run_pipeline()`** — The CLI flag is useless if it isn't wired to the pipeline call. Test must assert `run_pipeline` was called with the `top_n` kwarg.
- **Column width overflow** — 13 columns may get tight at console width < 120. Test with width=200 (matching the `test_options_chain.py` yield column test pattern).
- **Not updating help test** — `test_screener_help()` asserts all option names appear in `--help` output. Must add `--top-n` assertion.
- **Forgetting `_make_stock()` helper update** — The `test_display.py` helper needs a `perf_1m` kwarg to create test stocks with the new field.

## Open Risks

- **S01 not actually complete** — STATE.md says "planning", code has zero S01 deliverables. The roadmap `[x]` and doctor-placeholder summary are inconsistent. This is a hard blocker — S02 implementation depends on S01's three outputs: `perf_1m` field, `top_n` pipeline parameter, and the sort/cap logic.
- **`perf_1m` field shape uncertainty** — S01 context says percentage (e.g. `-5.2` for 5.2% decline, per TOPN-04 notes), but the actual implementation hasn't been written. If S01 stores it differently (e.g. as decimal `0.052`), the display formatter needs adjustment.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer (CLI) | — | none found (well-known framework, no skill needed) |
| Rich (tables) | — | none found (well-known framework, no skill needed) |
| pytest | — | none found (well-known framework, no skill needed) |

No external technologies new to this slice. All work uses existing project dependencies (Typer 0.24.1, Rich, pytest) with established patterns.

## Sources

- `scripts/run_screener.py` — current CLI structure, 4 existing Typer options
- `screener/display.py` — current table with 12 columns, all formatting helpers
- `tests/test_cli_screener.py` — 4 CLI tests with CliRunner + 8-patch mock pattern
- `tests/test_display.py` — table rendering tests, `_make_stock()` / `_all_pass_filters()` / `_capture_console()` helpers
- `tests/test_options_chain.py:637-675` — yield column test (most recent column addition pattern)
- `models/screened_stock.py` — current ScreenedStock fields (no `perf_1m` yet)
- `screener/pipeline.py:1191` — current `run_pipeline()` signature (no `top_n` yet)
- `.gsd/STATE.md` — shows S01 still in "planning" phase
- `.gsd/DECISIONS.md` — D041 (22-day lookback), D042 (CLI-only flag), D044 (None sorts last)
