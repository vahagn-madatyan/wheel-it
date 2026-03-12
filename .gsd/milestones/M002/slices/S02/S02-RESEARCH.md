# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 wires the `top_n` pipeline parameter (delivered by S01) to a `--top-n` CLI flag on `run-screener` and adds a "Perf 1M" column to the Rich results table. Both changes follow well-established patterns already in the codebase — Typer option declaration and Rich table column addition — with no new libraries, APIs, or architectural decisions needed.

The one prerequisite is that S01's branch (`gsd/M002/S01`) must be merged into the S02 branch before any code changes, since the `perf_1m` field on `ScreenedStock`, `compute_monthly_performance()`, and the `top_n` parameter on `run_pipeline()` all live on that unmerged branch.

## Recommendation

Merge S01 first, then make three surgical changes:

1. **CLI**: Add a `--top-n` `typer.Option` to the `run()` function in `scripts/run_screener.py` and pass it through to `run_pipeline(top_n=...)`.
2. **Display**: Add a "Perf 1M" column to `render_results_table()` using a new `fmt_signed_pct()` formatter (existing `fmt_pct` doesn't prepend "+" for positive values, which TOPN-05 requires).
3. **Tests**: CLI flag tests follow the `test_cli_screener.py` mock-heavy pattern; display column tests follow the `test_display.py` console-capture pattern.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option declaration | `typer.Option` with Annotated type hints | Already used for `--update-symbols`, `--verbose`, `--preset`, `--config` in same file |
| Console output capture for tests | `Console(file=StringIO(), width=120)` | Established in `test_display.py` — deterministic, no side effects |
| CLI invocation tests | `typer.testing.CliRunner` | Established in `test_cli_screener.py` — all existing CLI tests use it |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — CLI entry point. All options use `Annotated[type, typer.Option(...)]` pattern. The `run_pipeline()` call at line ~97 is where `top_n=` will be threaded through. Currently does not pass `top_n`.
- `screener/display.py:render_results_table()` — Builds a Rich `Table` with `add_column()` then `add_row()` for each passing stock. Columns are in a fixed order; "Perf 1M" should go before "Score" and after "Yield" (or after "HV%ile") to maintain logical grouping.
- `screener/display.py:fmt_pct()` — Formats as `f"{value:.1f}%"`. Does NOT prepend "+" for positive values. TOPN-05 spec says "+3.1%" format, so we need a `fmt_signed_pct()` variant.
- `tests/test_cli_screener.py` — 5 tests using `CliRunner`. Mock stack is deep (8 patches for `test_default_no_file_writes`). The `run_pipeline` mock must be updated to accept `top_n=` kwarg.
- `tests/test_display.py:TestRenderResultsTable` — 7 tests using `_make_stock()` helper and `_all_pass_filters()`. The `_make_stock` helper will need a `perf_1m` parameter.
- `models/screened_stock.py` — S01 adds `perf_1m: Optional[float]` field (on S01 branch, not yet merged).
- `screener/pipeline.py:run_pipeline()` — S01 adds `top_n: int | None = None` parameter (on S01 branch, not yet merged).

## Constraints

- **S01 branch must be merged first.** The `gsd/M002/S01` branch contains `perf_1m` field, `compute_monthly_performance()`, and `top_n` on `run_pipeline()`. These are not on the current `gsd/M002/S02` branch. Merge before coding.
- **`top_n` must be a positive integer or None.** Typer doesn't natively validate "positive integer" — need either a Typer callback or an early check in `run()`. A simple `if top_n is not None and top_n < 1` guard with `typer.Exit(code=1)` matches the existing error pattern (see `_raise_validation_error` and config error panel).
- **Backward compatibility (TOPN-06).** When `--top-n` is omitted, `top_n=None` passes through to `run_pipeline()`, which processes all stocks. No default cap value.
- **Column ordering matters.** The existing table has 13 columns (#, Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, HV%ile, Yield, Score, Sector). "Perf 1M" should go after "HV%ile" and before "Yield" — grouping it with the technical/market-data columns, before the options-derived columns.
- **Existing tests must still pass.** Current test count is 345+ (on main). S01 adds ~15 more. S02 must not break any.

## Common Pitfalls

- **Forgetting to thread `top_n` through to `run_pipeline()`.** The CLI flag parses fine but does nothing if the kwarg isn't forwarded. Test by asserting `run_pipeline` was called with `top_n=N`.
- **`fmt_pct` vs `fmt_signed_pct` confusion.** If we modify `fmt_pct` to always show "+", it would break existing columns (RSI, Margin, Growth, HV%ile) where "+" prefix is unexpected. Use a separate `fmt_signed_pct` function.
- **Mock stack drift in CLI tests.** The existing CLI tests patch 8 modules. Adding `top_n` requires no new patches, but the `mock_pipeline.assert_called_once()` assertions may need updating to `assert_called_once_with(...)` or `call_args` inspection to verify `top_n` threading.
- **`_make_stock` helper doesn't accept `perf_1m`.** Display tests use `_make_stock()` which will need a `perf_1m` keyword argument added.

## Open Risks

- **None significant.** All changes are additive (new CLI flag, new column, new formatter) with clear patterns to follow. S01's branch merge is the only prerequisite and it's a clean fast-forward candidate.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer (CLI framework) | — | none found — not needed, trivial API |
| Rich (terminal UI) | — | none found — not needed, established patterns in codebase |

## Sources

- Codebase exploration: `scripts/run_screener.py`, `screener/display.py`, `tests/test_cli_screener.py`, `tests/test_display.py`
- S01 branch diff: `git diff main..gsd/M002/S01` for `models/screened_stock.py`, `screener/market_data.py`, `screener/pipeline.py`, `tests/test_pipeline.py`, `tests/test_market_data.py`
- Milestone artifacts: M002-ROADMAP.md, M002-CONTEXT.md, DECISIONS.md, REQUIREMENTS.md
