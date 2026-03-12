---
id: S03
parent: M001
milestone: M001
provides:
  - "10 pure filter functions (4 Stage 1 + 6 Stage 2) each returning FilterResult"
  - "compute_historical_volatility for annualized HV from daily bars"
  - "run_stage_1_filters / run_stage_2_filters stage orchestration helpers"
  - "ScreenedStock.hv_30 field for historical volatility storage"
  - "compute_wheel_score: 3-component weighted scoring (capital efficiency 0.45, volatility 0.35, fundamentals 0.20)"
  - "fetch_universe: 2 Alpaca API calls for tradable universe + optionable set"
  - "load_symbol_list: reads symbols from text file with comment/empty line handling"
  - "run_pipeline: full 3-stage orchestrator (universe -> bars -> Stage 1 -> Stage 2 -> score -> sort)"
requires: []
affects: []
key_files: []
key_decisions:
  - "Filter functions are pure: take ScreenedStock + config, return FilterResult, never raise"
  - "market_cap stored in raw dollars on ScreenedStock; Finnhub millions conversion done in run_stage_2_filters"
  - "Stage 2 runner handles Finnhub data fetch + field population, keeping filter functions data-agnostic"
  - "HV computation uses log returns with ddof=1 std dev, annualized by sqrt(252)"
  - "Scoring weights: capital efficiency 0.45, volatility 0.35, fundamentals 0.20 -- capital efficiency is deliberately the dominant factor for wheel strategy"
  - "None HV and None fundamentals get neutral 0.5 score instead of elimination -- avoids penalizing stocks with partial data"
  - "Min-max normalization uses 0.5 fallback when all values are identical (single stock or equal metrics) to avoid division by zero"
  - "Fundamental sub-components averaged dynamically from available data: net margin, sales growth, debt/equity -- missing components excluded from average"
patterns_established:
  - "Filter function pattern: check None first -> check threshold -> return FilterResult with actual_value/threshold/reason"
  - "Stage runner pattern: run all filters regardless of individual outcome, append all results, return all-pass bool"
  - "Empty Finnhub profile triggers bulk fail with 'No Finnhub data available' reason"
  - "Scoring normalization: min-max across peer group with 0.5 fallback for degenerate cases"
  - "Pipeline orchestration: universe fetch -> bar fetch -> per-stock indicator computation -> stage filters -> score passing -> sort"
  - "No-bar-data stocks get FilterResult(bar_data, False) and skip all subsequent stages"
observability_surfaces: []
drill_down_paths: []
duration: 4min
verification_result: passed
completed_at: 2026-03-09
blocker_discovered: false
---
# S03: Screening Pipeline

**# Phase 03 Plan 01: Pipeline Filters Summary**

## What Happened

# Phase 03 Plan 01: Pipeline Filters Summary

**10 pure screening filter functions with HV computation, covering fundamentals/technicals/sector/optionability, all returning FilterResult with None-safe handling**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-09T00:00:59Z
- **Completed:** 2026-03-09T00:04:03Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 3

## Accomplishments
- 10 filter functions covering all screening criteria: price range, volume, RSI, SMA(200), market cap, debt/equity, net margin, sales growth, sector, optionability
- Historical volatility computation from daily bar data using log returns and annualization
- Stage runner helpers that orchestrate filter execution and Finnhub data fetching
- 40 unit tests covering pass/fail/None for every filter plus HV and stage runners

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests** - `be5f64e` (test)
2. **Task 1 (GREEN): Implementation** - `4cc02d8` (feat)

**Plan metadata:** `621a31e` (docs: complete plan)

_Note: TDD task with RED and GREEN commits_

## Files Created/Modified
- `screener/pipeline.py` - 10 filter functions, compute_historical_volatility, run_stage_1_filters, run_stage_2_filters
- `models/screened_stock.py` - Added hv_30: Optional[float] field to ScreenedStock
- `tests/test_pipeline.py` - 40 unit tests for all filters, HV computation, and stage runners

## Decisions Made
- Filter functions are pure: take ScreenedStock + config, return FilterResult, never raise exceptions
- market_cap is stored in raw dollars on ScreenedStock; the Finnhub millions-to-dollars conversion is done inside run_stage_2_filters when populating the field
- Stage 2 runner handles the full lifecycle: fetch Finnhub profile + metrics, populate stock fields, then run filters -- keeping individual filter functions data-source-agnostic
- HV computation uses numpy log returns with ddof=1 standard deviation, annualized by sqrt(252)
- filter_sma200 and filter_optionable support being disabled via config (pass-through when disabled)
- filter_sector uses case-insensitive matching for both include and exclude lists

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 10 filter building blocks ready for Plan 02 pipeline orchestration
- Stage runner helpers provide clean integration points for the full screening pipeline
- compute_historical_volatility ready for bar data from Alpaca market data module

## Self-Check: PASSED

- All 3 source/test files exist on disk
- Both commit hashes (be5f64e, 4cc02d8) verified in git log
- hv_30 field present in ScreenedStock model
- 13 public functions in screener/pipeline.py (10 filters + 1 HV + 2 runners)
- 101 tests pass (40 new + 61 existing), 0 failures

---
*Phase: 03-screening-pipeline*
*Completed: 2026-03-09*

# Phase 03 Plan 02: Scoring Engine & Pipeline Orchestrator Summary

**3-component weighted wheel-suitability scoring (0-100) with full universe-to-ranked-results pipeline orchestrating Alpaca/Finnhub data through 3 filtering stages**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-09T00:06:42Z
- **Completed:** 2026-03-09T00:10:49Z
- **Tasks:** 2 (TDD: RED + GREEN each)
- **Files modified:** 2

## Accomplishments
- Scoring engine with 3 weighted components: capital efficiency (0.45), volatility proxy (0.35), fundamental strength (0.20)
- Universe fetching via 2 Alpaca API calls (tradable equities + optionable set)
- Full pipeline orchestrator: universe -> bars -> indicators -> Stage 1 -> Stage 2 -> score -> sort
- 20 new tests (9 scoring + 11 universe/pipeline) for total of 60 pipeline tests

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Scoring tests** - `00f8a88` (test)
2. **Task 1 (GREEN): Scoring implementation** - `6f13042` (feat)
3. **Task 2 (RED): Universe/pipeline tests** - `445b87a` (test)
4. **Task 2 (GREEN): Universe/pipeline implementation** - `9b592d3` (feat)

_Note: TDD tasks with RED and GREEN commits_

## Files Created/Modified
- `screener/pipeline.py` - Added compute_wheel_score, fetch_universe, load_symbol_list, run_pipeline; added imports for Alpaca requests, Path, market_data functions
- `tests/test_pipeline.py` - 20 new tests: 9 for scoring (range, components, None handling, edge cases), 3 for fetch_universe, 2 for load_symbol_list, 6 for run_pipeline

## Decisions Made
- Scoring weights: capital efficiency 0.45, volatility 0.35, fundamentals 0.20 -- capital efficiency deliberately dominant for wheel strategy where tied-up capital per position matters most
- None HV and None fundamentals get neutral 0.5 score instead of elimination -- partial data should not be penalized when filters already validate key fields
- Min-max normalization falls back to 0.5 when min == max (single stock or identical values) -- avoids division by zero
- Fundamental sub-components (net margin, sales growth, debt/equity) averaged dynamically from available data -- missing individual metrics excluded from average rather than zeroed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Complete 3-stage screening pipeline ready for CLI integration
- run_pipeline returns all ScreenedStock objects (passing + eliminated) with filter_results populated for Phase 4 elimination reporting
- Scoring produces 0-100 scores with descending sort for ranked output display

## Self-Check: PASSED

- All 2 source/test files exist on disk
- All 4 commit hashes (00f8a88, 6f13042, 445b87a, 9b592d3) verified in git log
- 4 new public functions in screener/pipeline.py (compute_wheel_score, fetch_universe, load_symbol_list, run_pipeline)
- WEIGHT_CAPITAL_EFFICIENCY constant defined
- 60 pipeline tests pass, 0 failures

---
*Phase: 03-screening-pipeline*
*Completed: 2026-03-09*
