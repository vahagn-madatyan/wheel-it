# M002: Top-N Performance Cap — Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

## Project Description

Add a `--top-n` CLI flag to `run-screener` that limits how many stocks proceed past the cheap Stage 1 filters into the expensive per-symbol API calls. Sort Stage 1 survivors by ascending 1-month performance (worst performers first — best put-selling candidates) and take only the top N.

## Why This Milestone

The screener takes hours to run because every Stage 1 survivor goes through rate-limited per-symbol API calls: Finnhub earnings (~1.1s/symbol), Finnhub fundamentals (~1.1s/symbol), and Alpaca options chain lookups. With hundreds of Stage 1 survivors, this is impractical. Capping to N stocks (e.g. 20-50) makes the screener usable in minutes while prioritizing the most attractive put-selling candidates.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Run `run-screener --top-n 20` and get results in minutes instead of hours
- See a "Perf 1M" column in the results table showing each stock's recent performance
- Run `run-screener` without `--top-n` and get the same behavior as before (all stocks)

### Entry point / environment

- Entry point: `run-screener` CLI command
- Environment: local dev terminal
- Live dependencies involved: Alpaca API (bars already fetched), Finnhub API (calls reduced by cap)

## Completion Class

- Contract complete means: tests verify perf computation math, sort/cap logic, CLI flag parsing, display column, and backward compatibility
- Integration complete means: `run-screener --top-n 20` against live APIs produces results in reasonable time with Perf 1M column visible
- Operational complete means: none (batch CLI tool)

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- `run-screener --top-n 20` completes and shows ≤20 scored results with Perf 1M column
- `run-screener` (no flag) still processes all stocks as before
- All 345+ existing tests still pass

## Risks and Unknowns

- None significant — bar data (250 days) is already fetched, monthly perf is a simple computation, and the pipeline loop structure supports inserting a sort/cap step cleanly

## Existing Codebase / Prior Art

- `screener/pipeline.py:run_pipeline()` — Main pipeline loop; sort/cap inserts between Stage 1 and Stage 1b
- `screener/market_data.py:compute_indicators()` — Where perf_1m computation will be added
- `models/screened_stock.py:ScreenedStock` — Gains `perf_1m` field
- `screener/display.py:render_results_table()` — Gains "Perf 1M" column
- `scripts/run_screener.py` — Gains `--top-n` Typer option
- `screener/pipeline.py:run_pipeline()` — Gains `top_n` parameter

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- TOPN-01 through TOPN-06 — all six requirements are owned by this milestone

## Scope

### In Scope

- `compute_monthly_performance()` or inline computation from existing bar data
- `perf_1m` field on ScreenedStock
- Sort/cap logic in pipeline after Stage 1
- `--top-n` CLI flag on `run-screener`
- "Perf 1M" column in Rich results table
- Tests for all new functionality

### Out of Scope / Non-Goals

- Configurable performance lookback window (fixed at ~22 trading days)
- Per-preset top_n defaults (CLI-only flag)
- Changes to `run-call-screener` or `run-strategy`

## Technical Constraints

- Monthly perf uses ~22 trading days (close[-1] / close[-22] - 1) from existing 250-day bar data
- `top_n=None` means no cap (backward compatible)
- Sort/cap happens after Stage 1 filters but before Stage 1b earnings calls
- Stocks with insufficient bar data for perf computation get `perf_1m=None` and sort to end

## Integration Points

- Alpaca StockHistoricalDataClient — bar data already fetched in Step 3 of pipeline (no new calls)
- Pipeline loop — sort/cap inserts between existing Stage 1 and Stage 1b blocks

## Open Questions

- None — scope is well-defined
