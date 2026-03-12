---
phase: 03-screening-pipeline
plan: 02
subsystem: screening
tags: [scoring, pipeline-orchestrator, alpaca-universe, normalization, wheel-suitability]

# Dependency graph
requires:
  - phase: 03-screening-pipeline
    plan: 01
    provides: "10 filter functions, HV computation, stage runners (run_stage_1_filters, run_stage_2_filters)"
  - phase: 02-data-sources
    provides: "FinnhubClient with rate limiting, extract_metric with fallback chains"
  - phase: 01-foundation
    provides: "ScreenedStock/FilterResult models, ScreenerConfig with preset validation"
provides:
  - "compute_wheel_score: 3-component weighted scoring (capital efficiency 0.45, volatility 0.35, fundamentals 0.20)"
  - "fetch_universe: 2 Alpaca API calls for tradable universe + optionable set"
  - "load_symbol_list: reads symbols from text file with comment/empty line handling"
  - "run_pipeline: full 3-stage orchestrator (universe -> bars -> Stage 1 -> Stage 2 -> score -> sort)"
affects: [04-output-display, cli-entry-point, symbol-export]

# Tech tracking
tech-stack:
  added: []
  patterns: [min-max-normalization, neutral-0.5-for-missing-data, score-then-sort, cheap-before-expensive-filtering]

key-files:
  created: []
  modified:
    - screener/pipeline.py
    - tests/test_pipeline.py

key-decisions:
  - "Scoring weights: capital efficiency 0.45, volatility 0.35, fundamentals 0.20 -- capital efficiency is deliberately the dominant factor for wheel strategy"
  - "None HV and None fundamentals get neutral 0.5 score instead of elimination -- avoids penalizing stocks with partial data"
  - "Min-max normalization uses 0.5 fallback when all values are identical (single stock or equal metrics) to avoid division by zero"
  - "Fundamental sub-components averaged dynamically from available data: net margin, sales growth, debt/equity -- missing components excluded from average"

patterns-established:
  - "Scoring normalization: min-max across peer group with 0.5 fallback for degenerate cases"
  - "Pipeline orchestration: universe fetch -> bar fetch -> per-stock indicator computation -> stage filters -> score passing -> sort"
  - "No-bar-data stocks get FilterResult(bar_data, False) and skip all subsequent stages"

requirements-completed: [SCOR-01, SCOR-02]

# Metrics
duration: 4min
completed: 2026-03-09
---

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
