# M002: Top-N Performance Cap

**Vision:** Add a `--top-n` CLI flag to cap the number of stocks processed through expensive per-symbol API stages by sorting Stage 1 survivors by ascending 1-month performance and taking only the worst N performers — reducing screener runtime from hours to minutes while prioritizing the best put-selling candidates.

## Success Criteria

- `run-screener --top-n 20` processes only 20 stocks through Finnhub and options chain stages
- `run-screener` without `--top-n` processes all stocks as before (backward compatible)
- "Perf 1M" column appears in the results table with percentage values for each surviving stock
- Stocks are sorted by ascending monthly performance before the top-N cap is applied
- Stocks with insufficient bar data for perf computation are sorted to the end (not silently dropped)

## Key Risks / Unknowns

- None significant — uses existing bar data, simple computation, clean insertion point in pipeline

## Verification Classes

- Contract verification: pytest tests for perf computation math, sort/cap logic, CLI flag, display column, backward compatibility
- Integration verification: `run-screener --top-n 20` against live Alpaca + Finnhub APIs
- Operational verification: none (batch CLI tool)
- UAT / human verification: user runs `run-screener --top-n 20` and confirms fast completion with Perf 1M column

## Milestone Definition of Done

This milestone is complete only when all are true:

- `run-screener --top-n 20` completes and shows ≤20 scored results with Perf 1M column
- `run-screener` (no flag) processes all stocks (backward compatible)
- All existing 345+ tests pass plus new tests for perf computation and top-N logic
- Success criteria re-checked against live behavior

## Requirement Coverage

- Covers: TOPN-01, TOPN-02, TOPN-03, TOPN-04, TOPN-05, TOPN-06
- Partially covers: none
- Leaves for later: none
- Orphan risks: none

## Slices

- [ ] **S01: Monthly Perf + Pipeline Cap** `risk:medium` `depends:[]`
  > After this: `run_pipeline(top_n=20)` returns results from only the 20 worst-performing Stage 1 survivors, with `perf_1m` populated on all ScreenedStock objects that have bar data.

- [ ] **S02: CLI Flag + Display** `risk:low` `depends:[S01]`
  > After this: User runs `run-screener --top-n 20` and sees results with a "Perf 1M" column, completing in minutes instead of hours.

## Boundary Map

### S01 → S02

Produces:
- `screener/market_data.py` → `compute_monthly_performance(bars_df)` returning float percentage (or added to `compute_indicators()`)
- `models/screened_stock.py` → `perf_1m: Optional[float]` field on ScreenedStock
- `screener/pipeline.py` → `run_pipeline(top_n=None)` parameter; when set, sorts Stage 1 survivors by ascending `perf_1m` and takes top N before proceeding to Stage 1b/2/3
- `tests/` → tests for perf computation math, sort/cap logic, backward compatibility (top_n=None)

Consumes:
- nothing (first slice)

### S02 (terminal slice)

Produces:
- `scripts/run_screener.py` → `--top-n` Typer option passed through to `run_pipeline(top_n=N)`
- `screener/display.py` → "Perf 1M" column in `render_results_table()`
- `tests/` → tests for CLI flag parsing, display column rendering

Consumes from S01:
- `run_pipeline(top_n=N)` parameter
- `ScreenedStock.perf_1m` field for display
