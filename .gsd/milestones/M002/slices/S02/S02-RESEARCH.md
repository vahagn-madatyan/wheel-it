# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 adds the `--top-n` CLI flag to `run-screener` and a "Perf 1M" column to the Rich results table. However, **S01 was never actually implemented** — its summary is a doctor-created placeholder and no code changes exist in the codebase: `perf_1m` field is absent from `ScreenedStock`, `compute_monthly_performance()` doesn't exist, and `run_pipeline()` has no `top_n` parameter. S02 must therefore implement the full stack: perf computation, model field, pipeline sort/cap, CLI flag, and display column.

The implementation is straightforward. All required patterns already exist in the codebase — `compute_hv_percentile` in `pipeline.py` shows the exact pattern for a new computation from bar data, `hv_percentile` on `ScreenedStock` shows how to add an optional float field, the CLI uses Typer `Option` with clear patterns in `run_screener.py`, and the display module has consistent column-adding patterns in `render_results_table()`.

## Recommendation

Implement all six requirements (TOPN-01 through TOPN-06) in this slice since S01's work was never done. Structure into 3 tasks:

1. **T01: Model + Computation + Pipeline** — Add `perf_1m` to `ScreenedStock`, add perf computation to `compute_indicators()` (or inline in pipeline), add `top_n` param to `run_pipeline()` with sort/cap logic between Stage 1 and Stage 1b. Tests for math, sort, cap, backward compat.
2. **T02: CLI Flag** — Add `--top-n` Typer option to `run_screener.py`, wire it through to `run_pipeline(top_n=N)`. Tests for flag parsing and pipeline pass-through.
3. **T03: Display Column** — Add "Perf 1M" column to `render_results_table()`. Tests for column rendering and formatting.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | `typer.Option` | Already used for all 4 existing flags; consistent pattern |
| Rich table columns | `table.add_column()` / `table.add_row()` | Exact pattern in `render_results_table()` with 12 existing columns |
| Percentage formatting | `fmt_pct()` in `screener/display.py` | Already formats `X.X%` with None → "N/A" handling |

## Existing Code and Patterns

- `models/screened_stock.py` — Add `perf_1m: Optional[float] = None` field. Follow the pattern of `hv_percentile: Optional[float] = None` (L36). No factory or property needed — just a plain optional field.
- `screener/market_data.py:compute_indicators()` — Add monthly perf computation here. Bar data (`close` column) is already available. Pattern: check `len(close) >= 23` (need 22 prior days + current), compute `(close[-1] / close[-22] - 1) * 100`, return as `perf_1m` key. Follows the RSI/SMA pattern of returning None on insufficient data.
- `screener/pipeline.py:run_pipeline()` — Add `top_n: int | None = None` parameter. Insert sort/cap block at line ~1282 (after Stage 1 loop completes, before Stage 1b earnings). The pipeline currently processes each stock inline in a single loop — the sort/cap requires restructuring into: (1) build stocks + run Stage 1, (2) sort/cap Stage 1 survivors, (3) loop Stage 1b/2/3 on survivors only. This is the most complex change.
- `screener/pipeline.py` lines 1256–1282 — Current single-pass loop processes each stock through all stages inline. For top_n, need to split: first pass computes indicators + Stage 1 filters for all stocks, second pass (post sort/cap) runs Stage 1b/2/3 on survivors only.
- `scripts/run_screener.py` — Add `top_n` Typer option. Follow pattern of existing options (lines 67–78). Pass through to `run_pipeline(top_n=top_n)`. Pattern: `typer.Option("--top-n", help="...")` with `int | None` type.
- `screener/display.py:render_results_table()` — Add column after "HV%ile" (or after "Yield"). Use `fmt_pct()` for formatting. Add sign prefix for clarity (e.g. `-5.2%`, `+3.1%`). May need a new `fmt_signed_pct()` helper since existing `fmt_pct` doesn't add `+` for positives.
- `tests/test_cli_screener.py` — Shows pattern for CLI tests: mock `run_pipeline`, `load_config`, etc. with `@patch` decorators, invoke via `runner.invoke(app, ["--top-n", "20"])`.
- `tests/test_display.py:_make_stock()` — Helper factory. Needs `perf_1m` kwarg added to support new display tests. Pattern: optional keyword with default None.

## Constraints

- `run_pipeline()` currently uses a single loop that processes each stock inline through all stages. The top_n cap between Stage 1 and Stage 1b requires splitting this into two phases: all-stocks Stage 1, then survivors-only Stage 1b/2/3. This is the most significant structural change.
- `perf_1m` uses ~22 trading days lookback (D041). Computation: `(close.iloc[-1] / close.iloc[-22] - 1) * 100`. Needs `len(close) >= 22` minimum.
- `top_n=None` must mean no cap — backward compatible (D042, TOPN-06).
- `None` perf_1m sorts to end, not dropped (D044). Use `sort(key=lambda s: (s.perf_1m is None, s.perf_1m or 0))` for ascending sort with None-last.
- Cap placement: after Stage 1, before Stage 1b earnings calls (D043).
- 345 existing tests must continue passing.
- The project shadows stdlib `logging` with its own `logging/` package — use `import logging as stdlib_logging` (D001).

## Common Pitfalls

- **Pipeline loop restructuring** — The current single-pass loop must be split into two phases. Must ensure that stocks failing bar_data still get appended to the final list (they currently `continue` after appending). The restructuring must preserve the existing behavior where non-Stage-1-survivors still appear in final results for stage summary display.
- **None sort ordering** — Python cannot compare `None < float`. Must use a key function that handles None explicitly: `(perf_1m is None, perf_1m or 0)` puts None-values last in ascending sort.
- **Percentage sign in display** — `fmt_pct()` formats as `X.X%` but doesn't add `+` for positive values. For Perf 1M, positive returns should show `+3.1%` and negative `-5.2%`. Need a small formatting helper or inline logic.
- **Typer integer option with None default** — Use `int | None` type annotation with `default=None`. Typer handles this natively. Don't use `Optional[int]` from typing — the project uses `X | None` style (see `Callable | None` in pipeline.py).
- **Stage 1 survivors identification** — After restructuring, need to clearly identify which stocks passed Stage 1 (all filters passed so far) vs which stocks failed earlier stages but still need to appear in final results for display/summary purposes.

## Open Risks

- **Pipeline restructuring complexity** — Splitting the single-pass loop into two phases is the primary risk. The loop currently handles bar_data failures (early continue), Stage 1 failures (no further processing), and Stage 1b/2/3 sequentially. The restructured version must preserve identical behavior when `top_n=None` to avoid test regressions.
- **S01 placeholder summary** — S01 was marked complete by a doctor process but no code was written. The S02 plan must explicitly scope all S01 deliverables (TOPN-02, TOPN-03, TOPN-04) in addition to S02's own requirements (TOPN-01, TOPN-05, TOPN-06).

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer CLI | — | none found (standard library usage, no skill needed) |
| Rich tables | — | none found (standard library usage, no skill needed) |
| Python/pandas | — | none found (trivial computation) |

## Sources

- Codebase inspection: `screener/pipeline.py`, `screener/market_data.py`, `screener/display.py`, `scripts/run_screener.py`, `models/screened_stock.py`
- Test patterns: `tests/test_cli_screener.py`, `tests/test_display.py`
- Decision register: `.gsd/DECISIONS.md` (D041–D044)
- Requirements: `.gsd/REQUIREMENTS.md` (TOPN-01 through TOPN-06)
