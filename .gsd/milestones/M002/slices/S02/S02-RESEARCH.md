# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is a straightforward wiring slice. S01 (on branch `gsd/M002/S01`, not yet merged into this branch) delivered the `perf_1m` field on `ScreenedStock`, the `compute_monthly_performance()` function, and the `run_pipeline(top_n=None)` parameter with sort/cap logic — all with tests. S02 needs to: (1) add a `--top-n` Typer option to `scripts/run_screener.py` that passes through to `run_pipeline`, (2) add a "Perf 1M" column to the Rich results table in `screener/display.py`, and (3) write tests for both.

The S01 branch must be merged into `gsd/M002/S02` before any S02 code is written, since S02 depends on `ScreenedStock.perf_1m` and `run_pipeline(top_n=)` which only exist on S01's branch.

All three changes follow established patterns already in the codebase — Typer `Annotated` options (5 existing examples), Rich table columns (12 existing columns), and display test helpers (`_make_stock`, `_all_pass_filters`, `_capture_console`). No new libraries, no architectural decisions, no API calls.

## Recommendation

Merge `gsd/M002/S01` into `gsd/M002/S02` first. Then implement as a single task:

1. **CLI flag:** Add `top_n: Annotated[int | None, typer.Option("--top-n", ...)] = None` to `run()`, pass it to `run_pipeline(..., top_n=top_n)`.
2. **Display column:** Insert a "Perf 1M" column in `render_results_table()` between "HV%ile" and "Yield", using `fmt_pct(stock.perf_1m)` with sign-aware formatting.
3. **Tests:** CLI tests with Typer `CliRunner` (flag parsed → pipeline called with `top_n`; no flag → `top_n=None`). Display tests verifying "Perf 1M" header appears, values render correctly (`-5.2%`, `+3.1%`), `None` renders as "N/A".

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | Typer `Annotated[..., typer.Option()]` pattern | Already used for 5 options in this file |
| Table column rendering | `fmt_pct()` in `screener/display.py` | Handles None→"N/A" and decimal formatting |
| Test console capture | `_capture_console()` + `StringIO` pattern in `test_display.py` | Established pattern, consistent test style |
| CLI test invocation | `typer.testing.CliRunner` in `test_cli_screener.py` | Already used for all CLI tests |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — Entry point. All Typer options use `Annotated[T, typer.Option()]` pattern. `run_pipeline()` call at line 119 needs `top_n=top_n` kwarg added.
- `screener/display.py:render_results_table()` — 12 columns currently. New column inserts between "HV%ile" and "Yield". Follow existing pattern: `table.add_column(...)` then matching `table.add_row(...)` value.
- `screener/display.py:fmt_pct()` — Formats `float|None` as `X.X%` or `N/A`. Works for perf_1m but note: it doesn't add a `+` prefix for positive values. If we want `+3.1%` style, we need a small wrapper or new formatter.
- `tests/test_cli_screener.py` — 4 existing CLI tests using `CliRunner` with `@patch` decorators. New tests follow this exact mock-stack pattern.
- `tests/test_display.py:_make_stock()` — Helper for building `ScreenedStock` with specific fields. Needs a `perf_1m` parameter added.
- `tests/test_display.py:TestRenderResultsTable` — 7 existing tests. Add tests for Perf 1M column presence and formatting.
- `models/screened_stock.py` — `perf_1m: Optional[float]` field added by S01 (on S01 branch, not yet merged).
- `screener/pipeline.py:run_pipeline()` — `top_n` parameter added by S01 (on S01 branch, not yet merged).

## Constraints

- **S01 branch must be merged first.** `ScreenedStock.perf_1m` and `run_pipeline(top_n=)` only exist on `gsd/M002/S01`. Current branch has neither.
- **`top_n` must be `int | None`, not `int` with default 0.** `None` means "no cap" (backward compatible per TOPN-06 and D042). Typer needs explicit `None` default.
- **Column insertion order matters.** Rich tables are positional — the new column in `add_column()` must align with the matching value in `add_row()`. Insert "Perf 1M" between "HV%ile" (col 10) and "Yield" (col 11).
- **Existing 345 tests must still pass.** No breaking changes to function signatures used by other callers.
- **`fmt_pct()` doesn't add `+` sign.** The requirement says "formatted as percentage with sign (e.g. -5.2%, +3.1%)". Need either a new `fmt_pct_signed()` or a conditional wrapper. Negative values already get `-` from Python float formatting; positive values need explicit `+`.

## Common Pitfalls

- **Forgetting to merge S01 branch** — All S02 code depends on S01 deliverables that are only on `gsd/M002/S01`. Attempting to implement without merging will hit import errors and missing fields immediately.
- **Typer `int | None` default** — Typer handles `Optional[int]` with `None` default correctly via `Annotated[int | None, typer.Option()] = None`. But ensure the type hint is `int | None`, not just `int`, or Typer will require the flag on every invocation.
- **`add_row` positional mismatch** — Adding `add_column("Perf 1M")` without a corresponding value in `add_row()` (or in the wrong position) will silently misalign all subsequent columns. Count carefully.
- **Display test helper `_make_stock` doesn't accept `perf_1m`** — Need to add the parameter to the helper, or set it directly on the stock object after creation. The helper in `test_display.py` doesn't include all fields — it's selective.
- **Sign formatting in tests** — If tests assert `"+3.1%"` but the formatter produces `"3.1%"`, they'll fail. Decide the format in the formatter, then write tests to match.

## Open Risks

- **S01 merge conflicts.** The S01 branch modifies `pipeline.py`, `market_data.py`, `screened_stock.py`, and adds tests. The S02 branch currently matches `main`. Merge should be clean, but verify after.
- **`render_stage_summary` doesn't account for top-N cap.** The stage summary panel shows "Stage 1: N" but doesn't show a "Top-N cap: N → M" line. This is not required by TOPN-05 (which only requires the column), but users may find it confusing. Consider adding it as a minor enhancement, or leave for a future slice. Not blocking.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer (CLI framework) | — | none found — Typer is simple enough that docs aren't needed |
| Rich (terminal UI) | — | none found — existing codebase patterns are sufficient |

## Sources

- Codebase exploration: `scripts/run_screener.py`, `screener/display.py`, `models/screened_stock.py`, `screener/pipeline.py`, `tests/test_display.py`, `tests/test_cli_screener.py`
- S01 branch diff: `git diff main..gsd/M002/S01` — confirmed all S01 deliverables exist and are tested
- Requirements: TOPN-01, TOPN-05, TOPN-06 from `.gsd/REQUIREMENTS.md`
- Decisions: D042 (top_n is CLI-only), D044 (None perf_1m sorts last) from `.gsd/DECISIONS.md`
