# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 adds the `--top-n` CLI flag to `run-screener` and a "Perf 1M" column to the Rich results table. It owns requirements TOPN-01, TOPN-05, and TOPN-06.

**Critical finding:** S01 was marked complete by a doctor recovery, but **no S01 code was actually implemented**. The `perf_1m` field doesn't exist on `ScreenedStock`, `top_n` parameter doesn't exist on `run_pipeline()`, and `compute_monthly_performance()` doesn't exist. S02 must absorb all S01 deliverables (TOPN-02, TOPN-03, TOPN-04) in addition to its own scope. This is low-risk because the codebase is clean and the insertion points are well-defined, but the task list must include S01's work.

The changes touch four files plus tests: `models/screened_stock.py` (add field), `screener/market_data.py` (add perf computation), `screener/pipeline.py` (add `top_n` param + sort/cap logic), `scripts/run_screener.py` (add CLI flag), and `screener/display.py` (add column). All 345 existing tests pass. The pipeline loop must be split into two phases to insert the sort/cap between Stage 1 and Stage 1b.

## Recommendation

Implement as a single slice absorbing S01's undelivered work, in this order:

1. **ScreenedStock field** — Add `perf_1m: Optional[float] = None` to the dataclass
2. **Perf computation** — Add to `compute_indicators()` return dict (not a separate function — keeps it alongside other indicator computations, consistent with existing pattern)
3. **Pipeline restructure** — Split the single symbol loop into Phase 1 (indicators + Stage 1) and Phase 2 (Stage 1b/2/3). Add `top_n=None` parameter; when set, sort Phase 1 survivors by ascending `perf_1m` (None last) and take top N before Phase 2
4. **CLI flag** — Add `--top-n` Typer option (positive int, default None), pass through to `run_pipeline(top_n=N)`
5. **Display column** — Add "Perf 1M" column to `render_results_table()` using existing `fmt_pct()` helper with sign prefix
6. **Tests** — Perf math, sort/cap logic, backward compatibility, CLI flag, display column

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Percentage formatting | `screener.display.fmt_pct()` | Already handles None → "N/A" and `{value:.1f}%` |
| CLI option parsing | Typer `Annotated[int \| None, typer.Option()]` | Matches existing pattern in `run_screener.py` |
| Score coloring | `_score_style()` | Established pattern for table styling |
| Console capture in tests | `Console(file=StringIO(), width=120)` | Established pattern in `test_display.py` |

## Existing Code and Patterns

- `scripts/run_screener.py` — CLI uses `Annotated[type, typer.Option()]` pattern for all flags. `--top-n` follows this exact pattern. The `run_pipeline()` call at line ~108 passes all args through.
- `screener/display.py:render_results_table()` — Table columns added via `table.add_column()` followed by matching values in `table.add_row()`. "Perf 1M" inserts after "HV%ile" and before "Yield". Use `fmt_pct()` for formatting but add sign prefix for clarity.
- `screener/market_data.py:compute_indicators()` — Returns a dict with keys like `price`, `avg_volume`, `rsi_14`. Add `perf_1m` as a new key. Computation: `(close[-1] / close[-22] - 1) * 100` when `len(close) >= 22`, else `None`.
- `screener/pipeline.py:run_pipeline()` — Currently processes all stages in one loop per symbol. Must split into Phase 1 loop (indicators + Stage 1 filters) and Phase 2 loop (Stage 1b + Stage 2 + Stage 3) with sort/cap between them.
- `models/screened_stock.py` — Dataclass with Optional fields; `perf_1m` follows existing pattern alongside `hv_percentile`, `rsi_14`, etc.
- `tests/test_cli_screener.py` — Tests use `typer.testing.CliRunner` with heavy `@patch` decorators. New `--top-n` test follows `test_verbose_shows_filter_breakdown` pattern.
- `tests/test_display.py` — `_make_stock()` helper, `_all_pass_filters()`, and `_capture_console()` are reusable. Column header test at line 205 checks for all column names.
- `tests/test_pipeline.py` — Pipeline integration tests patch `fetch_daily_bars`, `compute_indicators`, `compute_historical_volatility`, `compute_hv_percentile`. New tests for `top_n` follow this pattern.

## Constraints

- **Loop split required (D043):** The cap goes between Stage 1 and Stage 1b. The current pipeline runs all stages inline per symbol. Phase 1 must complete for ALL symbols before the sort/cap can run, then Phase 2 runs only on survivors. This is the only structural change.
- **`perf_1m` uses 22 trading days (D041):** Fixed lookback. `close.iloc[-1] / close.iloc[-22] - 1` when `len(close) >= 22`.
- **None perf_1m sorts last (D044):** `sorted(survivors, key=lambda s: (s.perf_1m is None, s.perf_1m or 0))` — tuple sort puts `None` last.
- **top_n=None means no cap (D042, TOPN-06):** Pipeline behaves identically to current behavior. All 345 existing tests must still pass without modification.
- **67 pipeline tests exist:** The loop split must preserve identical behavior when `top_n=None`. All existing pipeline tests call `run_pipeline()` without `top_n`, so backward compatibility is exercised automatically.
- **Percentage with sign for display:** `fmt_pct()` doesn't include sign prefix. Either modify it (risky — 4 existing callers) or use a local `fmt_signed_pct()` helper.

## Common Pitfalls

- **Breaking existing pipeline tests with loop split** — The Phase 1/Phase 2 split changes control flow but must produce identical results when `top_n=None`. Run full test suite after restructure, before adding any new features.
- **Forgetting `perf_1m` in `_make_stock()` helper** — `test_display.py` uses `_make_stock()` to construct test stocks. If `perf_1m` isn't set, display tests will show "N/A" in the column, which may be fine for backward-compat tests but needs explicit values for new tests.
- **Pipeline test mocks returning indicators without `perf_1m`** — Existing `compute_indicators` mocks return dicts without `perf_1m`. The pipeline code must handle this gracefully (default to None).
- **Progress callback stage/total changes** — The loop split means progress stages fire differently. Existing progress tests (`test_pipeline_calls_on_progress`, `test_pipeline_finnhub_progress_includes_symbol`) may need adjustment.
- **Sign formatting for `fmt_pct`** — Current `fmt_pct()` outputs `-5.2%` for negatives but `5.2%` for positives (no `+` prefix). For perf display, `+3.1%` is more readable. Use a dedicated `fmt_signed_pct()` to avoid touching existing callers.

## Open Risks

- **Progress callback test sensitivity** — Two existing tests check progress callback invocation patterns. The loop split changes when callbacks fire (Phase 1 then Phase 2 instead of interleaved). These tests may need minor updates.
- **S01 summary is a doctor placeholder** — No S01 task summaries exist. This research serves as the authoritative analysis of what S01 was supposed to deliver and confirms none of it was implemented.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer (Python CLI) | `narumiruna/agent-skills@python-cli-typer` | available (13 installs) — low install count, not recommended |
| Rich (terminal UI) | none found | none found |

No skills are recommended for installation — the codebase already has well-established patterns for both Typer CLI options and Rich table rendering. The existing code in `scripts/run_screener.py` and `screener/display.py` serves as sufficient reference.

## Sources

- Codebase exploration: `scripts/run_screener.py`, `screener/display.py`, `screener/pipeline.py`, `screener/market_data.py`, `models/screened_stock.py`
- Test patterns: `tests/test_cli_screener.py` (5 tests), `tests/test_display.py` (30+ tests), `tests/test_pipeline.py` (67 tests)
- Decision register: D041–D044 (M002 decisions)
- S01 summary: doctor-created placeholder confirming no implementation was done
