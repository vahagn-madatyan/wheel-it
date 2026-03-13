# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 is a low-risk wiring slice that connects S01's `run_pipeline(top_n=N)` parameter to a `--top-n` Typer CLI option and adds a "Perf 1M" column to the Rich results table. All the hard work (two-pass pipeline refactor, sort/cap logic, `compute_monthly_performance()`, `perf_1m` field on ScreenedStock) is done on branch `gsd/M002/S01`. S02's job is strictly surface-level: one new CLI parameter, one new table column, and tests for both.

The S01 branch must be merged into `gsd/M002/S02` before implementation begins — the diff (`git diff gsd/M002/S02..gsd/M002/S01`) shows 917 additions across `models/screened_stock.py` (1 line: `perf_1m` field), `screener/market_data.py` (+17 lines: `compute_monthly_performance`), `screener/pipeline.py` (+84/-40: two-pass architecture with `top_n` param), and new tests in `test_market_data.py` and `test_pipeline.py`. No overlap with S02's target files.

The existing codebase has strong established patterns for both changes: Typer option patterns in `scripts/run_screener.py` (4 existing `Annotated[..., typer.Option()]` params), display column patterns in `screener/display.py` (`render_results_table()` with 12 columns, `fmt_pct()` helper), and comprehensive test patterns in `tests/test_display.py` (51 tests) and `tests/test_cli_screener.py` (5 tests with `CliRunner` + `@patch` decorators).

## Recommendation

Two tasks, sequential (both are trivial, ~20 LOC each):

1. **T01 — CLI flag**: Add `--top-n` option to `scripts/run_screener.py` using `Annotated[int | None, typer.Option("--top-n", min=1)]`, thread it into `run_pipeline(top_n=top_n)`. Test with `CliRunner` for: flag appears in `--help`, `None` default, value forwarding to pipeline, `min=1` validation (0 and negative rejected by Typer natively).

2. **T02 — Display column**: Add "Perf 1M" column to `render_results_table()` after "HV%ile" and before "Yield". Use a sign-aware format: `f"{value:+.1f}%"` (Python format spec handles `+`/`-` natively). Add tests verifying column presence and formatting for positive, negative, zero, and None values.

**Pre-task 0**: Merge `gsd/M002/S01` into current branch before any code changes.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option declaration | Typer `Annotated[..., typer.Option()]` pattern | 4 existing options in `run_screener.py` use this exact pattern |
| Input validation | `typer.Option(min=1)` | Verified with Typer 0.24.1: rejects 0 and negative with clean error message |
| Percentage formatting | `screener.display.fmt_pct()` | Already handles None→"N/A" and `{value:.1f}%`; just needs sign prefix for Perf 1M |
| CLI testing | `typer.testing.CliRunner` + `@patch` | 5 existing tests in `test_cli_screener.py` with same pattern |
| Console capture | `Console(file=StringIO(), width=120)` | `_capture_console()` helper in `test_display.py` |

## Existing Code and Patterns

- `scripts/run_screener.py:56-73` — Four `Annotated[..., typer.Option()]` params including `PresetName | None` optional enum. New `--top-n` follows same pattern with `int | None` type.
- `scripts/run_screener.py:119-126` — `run_pipeline()` call site. Add `top_n=top_n` kwarg here. Pipeline already accepts `top_n` parameter on S01 branch.
- `screener/display.py:180-193` — Column declarations in `render_results_table()`. 12 columns currently. "Perf 1M" goes between "HV%ile" and "Yield" (groups performance metrics).
- `screener/display.py:195-215` — `add_row()` call. New perf column value slots between `hv_pct_str` and `yield_str`.
- `screener/display.py:105-110` — `fmt_pct()` returns `f"{value:.1f}%"` without sign prefix. For Perf 1M, need `f"{value:+.1f}%"` to show `+3.1%` / `-5.2%` per TOPN-05. Either add `fmt_signed_pct()` or a `signed=True` param.
- `tests/test_display.py:30-58` — `_make_stock()` helper. Needs `perf_1m` kwarg added. Also `_all_pass_filters()` at line 62.
- `tests/test_cli_screener.py` — 5 tests using `CliRunner` with `@patch` on `scripts.run_screener.*` module-level imports. Same pattern for `--top-n` tests.
- `tests/test_display.py:205-213` — `test_table_has_column_headers` checks column names in rendered output. Add "Perf 1M" to the assertion list.

## Constraints

- **S01 merge required first**: Branch `gsd/M002/S01` has the `perf_1m` field, `compute_monthly_performance()`, and `run_pipeline(top_n=...)` parameter. Without merge, S02 code has nothing to wire to.
- **Merge is clean**: S01 modifies `models/screened_stock.py`, `screener/market_data.py`, `screener/pipeline.py`, and adds tests. S02 branch has only `.gsd/` changes. Zero source overlap.
- **Sign display required (TOPN-05)**: Format like `-5.2%` and `+3.1%`. Python's `f"{value:+.1f}%"` handles this natively — positive gets `+`, negative gets `-`.
- **Column position**: After "HV%ile", before "Yield" — groups performance metrics together.
- **Backward compatibility (TOPN-06)**: `--top-n` omitted → `top_n=None` → `run_pipeline()` processes all stocks. No default cap.
- **Typer 0.24.1 verified**: `int | None` with `min=1` works correctly — tested live. Zero exits 2 with "0 is not in the range x>=1".

## Common Pitfalls

- **Forgetting to thread `top_n` to `run_pipeline()`** — The Typer option exists but is never passed. Write a test that mocks `run_pipeline` and asserts `top_n` kwarg was forwarded.
- **`fmt_pct` doesn't show `+` sign** — Existing `fmt_pct` returns `5.2%` not `+5.2%`. Must use `f"{value:+.1f}%"` or a new helper for the Perf 1M column. Test both positive and negative values.
- **`_make_stock` helper missing `perf_1m`** — Test helper in `test_display.py` doesn't accept `perf_1m`. Forgetting to add it means all test stocks show "N/A" for Perf 1M.
- **Stale `.pyc` after merge** — Run `find . -name '__pycache__' -exec rm -rf {} + 2>/dev/null` after merging S01 branch.
- **Column count mismatch** — `add_column()` calls must match `add_row()` argument count exactly. Adding a column without adding the corresponding row value crashes Rich.

## Open Risks

- **Near-zero risk overall** — Both changes are mechanical wiring with strong existing patterns. S01 merge is the only prerequisite and the diff is clean.
- **No validation edge case for `top_n`** — Typer's `min=1` handles 0 and negatives. Very large values (e.g. 999999) are harmless — pipeline just processes all survivors when `top_n > len(survivors)`.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | — | none needed — core Python library, 4 existing patterns in codebase |
| Rich | — | none needed — core Python library, extensive in-project usage |

No external skills needed — both technologies are standard Python libraries with well-established patterns in the project.

## Sources

- `git diff gsd/M002/S02..gsd/M002/S01` — exact S01 API surface verified (`perf_1m` field, `run_pipeline(top_n=...)`, `compute_monthly_performance()`)
- `scripts/run_screener.py` — Typer option pattern with `Annotated[..., typer.Option()]` (4 existing params)
- `tests/test_cli_screener.py` — 5 CliRunner tests with `@patch` decorators on module-level imports
- `tests/test_display.py` — 51 display tests with `_make_stock` helper and `_capture_console`
- Live Typer 0.24.1 verification — confirmed `int | None` with `min=1` works: `None` default, valid int accepted, 0/-1 rejected with clean error
