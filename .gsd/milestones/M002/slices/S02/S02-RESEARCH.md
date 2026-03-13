# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 is a low-risk wiring slice: add a `--top-n` Typer option to `run-screener`, thread it through to `run_pipeline(top_n=N)`, and add a "Perf 1M" column to the Rich results table. All heavy logic (perf computation, sort/cap in pipeline) was built in S01 on the `gsd/M002/S01` branch. S02 consumes three S01 deliverables: the `top_n` parameter on `run_pipeline()`, the `perf_1m` field on `ScreenedStock`, and `compute_monthly_performance()`.

The implementation touches exactly two source files (`scripts/run_screener.py`, `screener/display.py`) and adds tests in the existing `tests/test_cli_screener.py` and `tests/test_display.py` files. Every pattern needed (Typer options, display columns, test fixtures) has a direct precedent in the codebase.

**Critical dependency:** S01 code changes live on `gsd/M002/S01` branch and must be merged into `gsd/M002/S02` before S02 implementation begins. Without the merge, `run_pipeline` lacks the `top_n` parameter and `ScreenedStock` lacks `perf_1m`.

## Recommendation

Merge `gsd/M002/S01` into `gsd/M002/S02` first, then implement in two small tasks:

1. **CLI flag** — Add `--top-n` Typer option + pass-through to `run_pipeline()`. Follow the exact pattern of `--verbose` / `--update-symbols` options. Use `int | None` with default `None` for backward compatibility. Add 3-4 tests.
2. **Display column** — Add "Perf 1M" column to `render_results_table()`. Add a `fmt_signed_pct()` helper (TOPN-05 requires `+3.1%` / `-5.2%` format, but existing `fmt_pct` only renders sign for negatives). Add 2-3 tests.

Both tasks are independent after the merge and could be done in either order.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | Typer `typer.Option()` with `Annotated` pattern | Already used for 4 options in `run_screener.py`; consistent UX |
| Rich table columns | `table.add_column()` + `table.add_row()` in `render_results_table()` | Exact pattern used for HV%ile and Yield columns added in S08/S09 |
| CLI testing | `typer.testing.CliRunner` + `@patch` decorators | 5 existing tests in `test_cli_screener.py` use this exact pattern |
| Display testing | `Console(file=StringIO(), width=...)` capture | 15+ tests in `test_display.py` use this pattern |

## Existing Code and Patterns

- `scripts/run_screener.py:56-73` — `run()` function with 4 existing Typer options. Add `top_n` as 5th parameter using identical `Annotated[int | None, typer.Option(...)]` pattern.
- `scripts/run_screener.py:101-106` — `run_pipeline()` call site. Add `top_n=top_n` kwarg here. Must match S01's signature: `run_pipeline(..., top_n: int | None = None)`.
- `screener/display.py:181-192` — Column definitions in `render_results_table()`. Insert "Perf 1M" column. Logical position: after "Price" (it's a price-derived metric) or before "Score" (it's a sort key). Recommendation: before "HV%ile" since both are technical metrics.
- `screener/display.py:108-112` — `fmt_pct()` returns `f"{value:.1f}%"` — no `+` sign for positives. TOPN-05 requires signed format. Add `fmt_signed_pct()` that uses `f"{value:+.1f}%"` (Python's `+` format specifier handles this natively).
- `tests/test_cli_screener.py` — 5 existing tests using `CliRunner` + `@patch` stack. Pattern: patch all dependencies (`run_pipeline`, `create_broker_client`, `require_finnhub_key`, `FinnhubClient`, `progress_context`, `render_*`), invoke `app` with args, assert exit code + mock calls.
- `tests/test_display.py` — `_make_stock()` helper, `_all_pass_filters()`, `_capture_console()`. Extend `_make_stock()` to accept `perf_1m` parameter.
- `tests/test_options_chain.py:637-690` — `TestDisplayYieldColumn` is the exact precedent for testing a new display column: create stock with field set, render, check column header + formatted value in output.

## Constraints

- **S01 merge required** — `run_pipeline(top_n=N)` and `ScreenedStock.perf_1m` only exist on `gsd/M002/S01` branch. S02 branch diverged from `main` which lacks these.
- **Typer 0.24.1** — `int | None` union type with `typer.Option(default=None)` is supported. No `Optional[int]` workaround needed.
- **345 existing tests must pass** — After S01 merge, run full suite to verify clean baseline before adding new tests.
- **Column width** — Results table already has 13 columns. Adding "Perf 1M" makes 14. Test at `width=200` to ensure no wrapping issues (precedent: `test_options_chain.py:660` uses `width=200`).
- **`_make_stock()` in test_display.py** — Currently doesn't accept `perf_1m` kwarg. Must add it (with `None` default) to avoid breaking existing test calls.

## Common Pitfalls

- **Forgetting `+` sign for positive perf** — `fmt_pct(3.1)` → `"3.1%"` but TOPN-05 requires `"+3.1%"`. Use Python's `f"{value:+.1f}%"` format specifier which adds `+` for positive, `-` for negative automatically. Don't modify existing `fmt_pct` — create `fmt_signed_pct` to avoid changing behavior for other columns.
- **`top_n` as string from CLI** — Typer handles `int | None` correctly: `--top-n 20` becomes `int(20)`, omitted becomes `None`. No manual conversion needed.
- **Mock stack order in CLI tests** — `@patch` decorators apply bottom-up. The existing `test_default_no_file_writes` has 8 stacked `@patch` decorators. Adding more requires careful parameter ordering. Follow exact stack pattern.
- **Column/row count mismatch** — Adding a column to `add_column()` without adding the corresponding value to `add_row()` raises `ValueError`. Must add both atomically.

## Open Risks

- **S01 merge conflicts** — S01 modifies `pipeline.py` (major refactor of `run_pipeline`) and `models/screened_stock.py`. S02 branch has neither change. Merge should be clean since S02 hasn't touched these files, but verify after merge.
- **S01 tests on merge** — S01 added ~10 new tests in `test_pipeline.py` and `test_market_data.py`. Must verify they pass on the merged branch.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | — | none found (standard Python library, no skill needed) |
| Rich | — | none found (standard Python library, no skill needed) |

## Sources

- Codebase inspection of `scripts/run_screener.py`, `screener/display.py`, `tests/test_cli_screener.py`, `tests/test_display.py`, `tests/test_options_chain.py`
- S01 branch diff (`git diff gsd/M002/S02..gsd/M002/S01`) for delivered API surface
- Python format spec: `f"{value:+.1f}"` adds sign prefix for both positive and negative floats
