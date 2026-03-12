# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is a thin wiring slice. S01 (on branch `gsd/M002/S01`, not yet merged) already implemented all the hard parts: `compute_monthly_performance()`, the `perf_1m` field on `ScreenedStock`, and the `top_n` parameter on `run_pipeline()` with sort/cap logic. S02 just needs to: (1) add a `--top-n` Typer option to `scripts/run_screener.py` and pass it through, (2) add a "Perf 1M" column to `render_results_table()` in `screener/display.py`, and (3) write tests for both.

The codebase has clear, consistent patterns for both changes. The CLI uses `Annotated[type, typer.Option(...)]` parameters (5 existing examples). The display table has 12 existing columns with established formatting helpers (`fmt_pct` handles the percentage display). Tests follow established patterns: `test_cli_screener.py` uses `CliRunner` with `@patch` decorators, and `test_display.py` uses `_capture_console()` + string assertions on output.

The only prerequisite is that `gsd/M002/S01` must be merged into the S02 branch first — without it, there's no `top_n` parameter to wire or `perf_1m` field to display.

## Recommendation

Merge S01 branch into S02 branch first, then implement two small changes:

1. **CLI flag:** Add `top_n: Annotated[int | None, typer.Option("--top-n", ...)] = None` parameter to the `run()` function, pass it to `run_pipeline(..., top_n=top_n)`. Follow the exact pattern of existing options like `--verbose` and `--update-symbols`.

2. **Display column:** Add `table.add_column("Perf 1M", justify="right")` in `render_results_table()`, positioned before "Score" (after "HV%ile" or "Yield"). Format with `fmt_pct()` — it already handles `None → "N/A"` and produces the `X.X%` format. The sign is inherent in the value (negative numbers display with `-`), but consider using a `+` prefix for positive values for clarity.

Both changes are mechanical and low-risk.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Percentage formatting | `screener.display.fmt_pct()` | Already handles None→"N/A", produces `X.X%` format |
| CLI option declaration | `Annotated[type, typer.Option()]` pattern | 5 existing examples in the same file; consistency |
| CLI testing | `typer.testing.CliRunner` + `@patch` | Established in `test_cli_screener.py` |
| Display testing | `_capture_console()` + string assertions | Established in `test_display.py` |

## Existing Code and Patterns

- `scripts/run_screener.py` — CLI entry point. All options use `Annotated[type, typer.Option("--flag-name", help="...")]` pattern. The `run_pipeline()` call at line 119 is where `top_n=top_n` gets added.
- `screener/display.py:render_results_table()` — 12-column Rich table. Column order: #, Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, HV%ile, Yield, Score, Sector. "Perf 1M" slots in naturally after "Yield" (before "Score").
- `screener/display.py:fmt_pct()` — Returns `"N/A"` for None, `f"{value:.1f}%"` for floats. Works for `perf_1m` display as-is, though positive values won't have a `+` prefix.
- `tests/test_cli_screener.py` — 5 tests using `CliRunner`. The `test_default_no_file_writes` test patches 8 modules and asserts `run_pipeline` was called. New test should verify `top_n` kwarg is passed through.
- `tests/test_display.py` — 45 tests. `_make_stock()` helper creates `ScreenedStock` with optional fields. `test_table_has_column_headers` asserts column names appear in output — needs "Perf 1M" added. The helper needs a `perf_1m` parameter.
- `models/screened_stock.py` — On S01 branch, has `perf_1m: Optional[float] = None` at line 40 (after `hv_percentile`). On current branch (main/S02), this field doesn't exist yet.
- `screener/pipeline.py` — On S01 branch, `run_pipeline()` accepts `top_n: int | None = None`. On current branch, no `top_n` parameter.

## Constraints

- **S01 must merge first.** The `perf_1m` field, `compute_monthly_performance()`, and `top_n` parameter on `run_pipeline()` all live on `gsd/M002/S01` branch. Without merging, S02 code has nothing to wire.
- **`top_n` must be `int | None`, not `int` with default 0.** `None` means "no cap" (backward compatible, per D042/TOPN-06). Typer handles `Optional[int]` correctly — default `None` means flag is omitted.
- **Column order matters.** "Perf 1M" should go near the end but before "Score" and "Sector" to maintain the logical flow: data columns → performance → score → metadata.
- **`fmt_pct` doesn't add `+` prefix for positive values.** The requirement (TOPN-05) says "formatted as percentage with sign (e.g. -5.2%, +3.1%)". This means we need a custom formatter or a wrapper around `fmt_pct` that adds `+` for positive values.
- **Existing test `test_table_has_column_headers` must be updated.** It asserts specific column names; adding "Perf 1M" means updating this test.

## Common Pitfalls

- **Forgetting to merge S01 branch** — All S02 changes depend on S01's `perf_1m` field and `top_n` parameter. If S01 isn't merged, imports fail and tests break.
- **Typer `int | None` syntax** — Use `Annotated[int | None, typer.Option(...)] = None`. Typer 0.9+ handles this correctly. Do NOT use `Optional[int]` in `Annotated` — `int | None` is the modern pattern already used in the codebase (`PresetName | None`).
- **Positive percentage sign** — `fmt_pct()` doesn't add `+` for positive values. Need `fmt_signed_pct()` or inline formatting like `f"+{value:.1f}%" if value > 0 else f"{value:.1f}%"`. Zero should display as `0.0%` (no sign).
- **Test helper `_make_stock` doesn't accept `perf_1m`** — Must add `perf_1m: float | None = None` parameter and `s.perf_1m = perf_1m` assignment to the helper in `test_display.py`.

## Open Risks

- **S01 branch merge conflicts** — S01 modifies `screener/pipeline.py` (84 lines changed), `models/screened_stock.py` (+1 line), `screener/market_data.py` (+17 lines), and test files (+334 lines). Merge into S02 should be clean since S02 hasn't touched these files, but verify.
- **S01 placeholder summary** — The S01 summary was doctor-generated. The actual S01 task summaries in `tasks/` should be consulted if anything is unclear about S01's implementation.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer (Python CLI) | `narumiruna/agent-skills@python-cli-typer` | available (13 installs — low adoption, skip) |
| Rich (Python tables) | none found | none found |

No skills worth installing — the changes are mechanical and the codebase patterns are well-established.

## Sources

- `scripts/run_screener.py` — existing CLI patterns (5 Typer options, `run_pipeline()` call site)
- `screener/display.py` — existing table columns and formatting helpers
- `tests/test_cli_screener.py` — existing CLI test patterns (CliRunner + patch)
- `tests/test_display.py` — existing display test patterns (45 tests, `_make_stock` helper)
- `git diff main..gsd/M002/S01` — S01 implementation details (pipeline, model, market_data changes)
- `.gsd/DECISIONS.md` — D041 (22-day lookback), D042 (CLI-only top_n), D043 (cap placement), D044 (None sorts last)
