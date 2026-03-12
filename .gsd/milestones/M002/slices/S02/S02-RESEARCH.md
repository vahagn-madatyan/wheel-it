# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 wires two things into the existing screener: (1) a `--top-n N` Typer option on `run-screener` that passes through to `run_pipeline(top_n=N)`, and (2) a "Perf 1M" column in `render_results_table()` showing `ScreenedStock.perf_1m`. Both are thin integration layers over S01's completed work — `run_pipeline` already accepts `top_n`, `ScreenedStock` already has `perf_1m`, and the display module already has the column-adding pattern established.

The S01 branch (`gsd/M002/S01`) contains all prerequisite code but has not been merged into this branch yet. S02's first task must merge S01 before any implementation can begin. After merge, the work is straightforward: one new Typer `Option` parameter, one `add_column` + `add_row` field in the table renderer, and tests for both.

## Recommendation

Merge S01 branch first, then implement in two small tasks: (1) CLI `--top-n` flag + tests, (2) "Perf 1M" display column + tests. Both tasks are low-risk with clear patterns to follow from existing code. No new libraries or patterns needed.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | Typer `Annotated[int \| None, typer.Option(...)]` | Already used for all other flags in `run_screener.py` |
| Table rendering | Rich `Table.add_column()` + row formatting | Established pattern in `render_results_table()` |
| CLI testing | `typer.testing.CliRunner` + `unittest.mock.patch` | Existing pattern in `test_cli_screener.py` |
| Display testing | `Console(file=StringIO())` capture pattern | Existing pattern in `test_display.py` |

## Existing Code and Patterns

- **`scripts/run_screener.py`** — Entry point. Has 4 Typer options already (`--update-symbols`, `--verbose`, `--preset`, `--config`). S02 adds `--top-n` following the same `Annotated[type, typer.Option(...)]` pattern. The `run_pipeline()` call at line 119 needs `top_n=top_n` kwarg added.
- **`screener/display.py:render_results_table()`** — Builds Rich table with 12 columns. "Perf 1M" column inserts between "HV%ile" and "Yield" (or at another logical position). Uses `fmt_pct()` helper for percentage formatting — reuse for perf_1m. Existing columns show sign for positive values only implicitly; perf_1m should show explicit `+`/`-` sign.
- **`screener/display.py:fmt_pct()`** — Returns `"{value:.1f}%"`. Does NOT include a sign prefix. For perf_1m, a custom format `f"{value:+.1f}%"` is needed to show `+3.1%` / `-5.2%` per TOPN-05.
- **`tests/test_cli_screener.py`** — 5 existing tests with heavy patching. Pattern: patch `run_pipeline`, `create_broker_client`, etc., then invoke via `CliRunner`. The `--top-n` test should verify `run_pipeline` is called with `top_n=N`.
- **`tests/test_display.py`** — `_make_stock()` helper builds `ScreenedStock` but does NOT accept `hv_percentile`, `put_premium_yield`, or `perf_1m` kwargs. Helper needs extension for `perf_1m` parameter. Console capture via `Console(file=StringIO(), width=120)`.
- **`models/screened_stock.py`** — `perf_1m: Optional[float]` field already added by S01 (on S01 branch). Located in "Technical indicators" section after `hv_percentile`.
- **`screener/pipeline.py`** — `run_pipeline(top_n=None)` parameter already added by S01 (on S01 branch). Just needs the CLI to pass it through.

## Constraints

- **S01 merge required** — `gsd/M002/S01` branch must be merged into `gsd/M002/S02` before implementation. S01 adds `perf_1m` field, `compute_monthly_performance()`, and `top_n` parameter to `run_pipeline`. Without merge, imports and field references will fail.
- **Typer 0.24.1** — Uses `Annotated` type hints (modern Typer pattern). `int | None` union syntax requires Python 3.10+ (project already uses this elsewhere).
- **`top_n` must be positive integer or None** — Typer `Option` with `int | None` type handles this. Consider adding `min=1` validation or Typer's `min` parameter.
- **Backward compatibility** — `run-screener` without `--top-n` must behave identically to current behavior (`top_n=None` → no cap). This is already handled by `run_pipeline`'s default.
- **D019 (module-level imports)** — CLI entry points must use module-level imports for patchability with `unittest.mock.patch`. Already followed in `run_screener.py`.
- **D015 (console injection)** — Display functions accept `console` parameter for testability. Already followed.

## Common Pitfalls

- **`_make_stock()` helper doesn't accept all fields** — `test_display.py`'s `_make_stock()` only accepts a subset of ScreenedStock fields. Adding `perf_1m` to tests requires extending the helper or setting the field directly after construction. Setting directly (`stock.perf_1m = -5.2`) is simpler and consistent with how tests handle `hv_percentile`.
- **Sign formatting** — `fmt_pct()` returns `"5.0%"` not `"+5.0%"`. TOPN-05 spec says "with sign (e.g. -5.2%, +3.1%)". Need a separate formatter or inline `f"{value:+.1f}%"` for the perf_1m column. Don't modify `fmt_pct()` — it's used by RSI, margin, growth, etc. where `+` prefix is inappropriate.
- **Column ordering** — The table has 12 columns. "Perf 1M" logically fits after "HV%ile" (both are technical/market indicators) and before "Yield" (which is options-derived). Column order: `... HV%ile | Perf 1M | Yield | Score | Sector`.
- **N/A for None perf_1m** — Stocks with `perf_1m=None` (insufficient bar data) should show "N/A" in the column, consistent with how HV%ile and Yield handle None.

## Open Risks

- **S01 merge conflicts** — The S02 branch diverged from S01's parent. Merge should be clean since S02 only has GSD artifacts (no code changes), but verify post-merge that all 345 existing tests still pass.
- **`--top-n 0` edge case** — If user passes `--top-n 0`, `run_pipeline` would return all stocks with none going through Stage 1b/2/3. Typer doesn't enforce `min=1` by default. Should validate or document. Low severity — weird input, graceful degradation.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | — | none found (no available skill; Typer 0.24.1 is well-documented and simple) |
| Rich | — | none found (Rich table API is straightforward) |

No relevant skills needed — this slice uses only Typer option declaration and Rich table column addition, both with established project patterns.

## Sources

- S01 branch diff (`git diff cd06247..424a33a`) — authoritative source for `top_n` pipeline parameter and `perf_1m` field implementation
- `scripts/run_screener.py` — existing CLI option patterns (Annotated + typer.Option)
- `screener/display.py` — existing column/formatting patterns
- `tests/test_cli_screener.py` — existing CLI test patterns (CliRunner + patch stack)
- `tests/test_display.py` — existing display test patterns (Console capture + StringIO)
