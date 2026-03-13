# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 is a low-risk terminal slice that wires two things together: (1) a `--top-n N` Typer option on `run-screener` that passes through to `run_pipeline(top_n=N)`, and (2) a "Perf 1M" column in the Rich results table showing `ScreenedStock.perf_1m`. Both consume S01 outputs that already exist on the `gsd/M002/S01` branch — `run_pipeline(top_n=)` parameter, `ScreenedStock.perf_1m` field, and `compute_monthly_performance()`.

The primary execution risk is **branch integration**: S02's branch diverged from `cd06247` before S01's work was committed. S01 modified `screener/pipeline.py`, `screener/market_data.py`, `models/screened_stock.py`, and test files. S02 must merge or rebase onto S01 before making its own changes, or conflicts will arise. The code changes themselves are minimal and follow well-established patterns.

A secondary design detail: TOPN-05 requires signed formatting (`+3.1%`, `-5.2%`) but the existing `fmt_pct()` only shows signs on negative values. A small formatting helper is needed.

## Recommendation

1. **Merge S01 into S02 branch first** — `git merge gsd/M002/S01` into `gsd/M002/S02`. S01 touched `pipeline.py` (run_pipeline signature + two-pass architecture), `market_data.py` (+`compute_monthly_performance`), `screened_stock.py` (+`perf_1m` field), and test files. S02 will touch different files (`scripts/run_screener.py`, `screener/display.py`) plus test additions, so the merge should be clean.

2. **CLI flag**: Add `top_n: Annotated[int | None, typer.Option("--top-n", min=1, ...)] = None` to the `run()` command, pass it through to `run_pipeline(..., top_n=top_n)`.

3. **Display column**: Add `table.add_column("Perf 1M", justify="right")` after "HV%ile" column. Use a signed percentage formatter (`+X.X%` / `-X.X%` / `0.0%`). Add the column value via `stock.perf_1m`.

4. **Tests**: CLI test with `@patch` verifying `top_n` passes through to `run_pipeline`. Display test verifying "Perf 1M" column header and signed value formatting. Backward compat test confirming no `--top-n` means `top_n=None`.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | Typer `Annotated[int \| None, typer.Option()]` | Already used for all 4 existing CLI options; consistent pattern |
| Rich table column | `table.add_column()` + `table.add_row()` | Identical pattern used for all 13 existing columns |
| Console capture in tests | `Console(file=StringIO(), width=120)` | Used in all 30+ display tests |
| CLI test runner | `typer.testing.CliRunner` + `@patch` | Used in all 5 existing CLI tests |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — CLI entry point with 4 Typer options using `Annotated[type, typer.Option()]` syntax. S02 adds a 5th option (`--top-n`). The `run_pipeline()` call at line ~97 needs `top_n=top_n` kwarg added.
- `screener/display.py:render_results_table()` — Rich table with 13 columns. "Perf 1M" column inserts after "HV%ile" (line 190) and before "Yield" (line 191). Follows the `fmt_pct()` pattern for percentage display but needs sign-aware formatting.
- `screener/display.py:fmt_pct()` — Returns `f"{value:.1f}%"` which gives `-3.7%` for negative but `3.7%` for positive (no `+` prefix). TOPN-05 requires explicit sign. Add a `fmt_signed_pct()` helper or use inline `f"{value:+.1f}%"`.
- `tests/test_cli_screener.py` — 5 CLI tests using `CliRunner` + extensive `@patch` stacks. The `test_default_no_file_writes` test patches 8 modules; S02's top_n test follows the same pattern but adds `["--top-n", "20"]` to `runner.invoke()` args.
- `tests/test_display.py:_make_stock()` — Helper for creating test `ScreenedStock` objects. Needs `perf_1m` parameter added (follows pattern of other Optional[float] fields like `rsi_14`).
- `tests/test_display.py:TestRenderResultsTable` — 7 existing tests for table rendering. Add 1-2 tests for "Perf 1M" column presence and signed value formatting.

## Constraints

- **Branch dependency**: S02 branch (`gsd/M002/S02`) forked from `cd06247` and does NOT contain S01's changes. Must merge `gsd/M002/S01` first. S01 modified: `screener/pipeline.py` (two-pass architecture + `top_n` param), `screener/market_data.py` (+`compute_monthly_performance`), `models/screened_stock.py` (+`perf_1m` field), `tests/test_market_data.py` (+6 tests), `tests/test_pipeline.py` (+270 lines, `TestTopNPipelineCap` class).
- **Typer 0.24.1**: `typer.Option` supports `min` parameter for integer validation. `int | None` type with `default=None` makes the flag optional. Hyphenated flag `--top-n` maps to Python parameter `top_n` automatically.
- **D019 (Module-level imports)**: CLI entry points use module-level imports for `@patch` discoverability. S02 doesn't add new imports to `run_screener.py` (only adds a parameter to existing `run_pipeline` call).
- **D042 (CLI-only)**: `top_n` is a CLI concern — not configurable via preset YAML. No changes to `ScreenerConfig` or preset files.
- **345 existing tests** must pass after changes. S01 added ~12 tests, bringing expected total to ~357.

## Common Pitfalls

- **Forgetting to merge S01 branch** — Without S01's changes, `run_pipeline` has no `top_n` parameter, `ScreenedStock` has no `perf_1m` field, and `compute_monthly_performance` doesn't exist. All S02 code would fail. Merge first.
- **`fmt_pct` vs signed formatting** — Using existing `fmt_pct()` for Perf 1M would omit the `+` sign on positive values. TOPN-05 explicitly requires `+3.1%` format. Use `f"{value:+.1f}%"` or a dedicated `fmt_signed_pct()`.
- **Typer hyphen-to-underscore mapping** — `--top-n` automatically maps to Python parameter `top_n`. Don't use `--top_n` (underscore) — Typer convention is hyphens in CLI flags.
- **Test patch target for `run_pipeline`** — The mock must be `@patch("scripts.run_screener.run_pipeline")` (not `@patch("screener.pipeline.run_pipeline")`) because `run_screener.py` uses a module-level import (D019). Existing tests already do this correctly.
- **Column order in test assertions** — When checking table output for "Perf 1M", the column header string appears in the Rich output. Verify with `assert "Perf 1M" in output`, matching the HV%ile/Yield test pattern.

## Open Risks

- **S01 placeholder summary** — The S01 slice summary was doctor-created and lacks real diagnostic info. The actual S01 code on `gsd/M002/S01` has been verified here (diff inspected — `perf_1m` field, `top_n` parameter, `compute_monthly_performance`, 12+ tests all present). No functional risk, but the GSD state tracking is incomplete.
- **Typer `min` parameter availability** — Typer 0.24.1 supports `min`/`max` on numeric Options, but if it doesn't work as expected, a manual `if top_n is not None and top_n < 1: raise typer.BadParameter(...)` check is a clean fallback.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | — | none found (simple API, codebase has 4 working examples) |
| Rich | — | none found (simple API, codebase has extensive patterns) |
| Python/pytest | — | none needed (well-established patterns in 345 tests) |

## Sources

- `scripts/run_screener.py` — Inspected CLI entry point; 4 existing Typer options, `run_pipeline` call
- `screener/display.py` — Inspected table rendering; 13 columns, `fmt_pct()` helper, `_score_style()` pattern
- `models/screened_stock.py` — Confirmed current state (no `perf_1m` yet — lives on S01 branch)
- `tests/test_display.py` — 30+ tests; `_make_stock()` helper, `Console(file=StringIO())` capture pattern
- `tests/test_cli_screener.py` — 5 tests; `CliRunner` + `@patch` stack pattern
- `git diff cd06247..gsd/M002/S01` — Verified S01 outputs: `perf_1m` field, `top_n` param, `compute_monthly_performance`, 12+ tests
- `pyproject.toml` — Typer 0.24.1, `run-screener` console_scripts entry
