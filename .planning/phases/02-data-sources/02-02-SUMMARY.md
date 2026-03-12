---
phase: 02-data-sources
plan: 02
subsystem: data
tags: [alpaca, ta, rsi, sma, pandas, technical-indicators]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "screener package structure, ScreenedStock model, logging shadow pattern"
provides:
  - "fetch_daily_bars() for batched Alpaca bar retrieval with split adjustment"
  - "compute_indicators() for RSI(14), SMA(200), price, avg_volume, above_sma200"
affects: [03-screening-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns: ["pd.bdate_range for deterministic test date generation", "pd.isna() NaN-to-None conversion for ta library outputs"]

key-files:
  created:
    - screener/market_data.py
    - tests/test_market_data.py
  modified: []

key-decisions:
  - "Used pd.bdate_range with fixed end date in tests instead of datetime.now() to avoid non-deterministic business-day alignment issues"
  - "Minimum 30 bars required for RSI(14) computation, 200 bars for SMA(200) -- below threshold returns None"

patterns-established:
  - "NaN-to-None: Always check pd.isna() before returning ta library outputs to prevent float NaN from leaking into ScreenedStock fields"
  - "Batched bar fetching: No limit parameter on multi-symbol StockBarsRequest to avoid total-across-symbols truncation"

requirements-completed: [SAFE-04]

# Metrics
duration: 3min
completed: 2026-03-08
---

# Phase 2 Plan 02: Market Data Summary

**Alpaca bar fetching in configurable batches with RSI(14) and SMA(200) indicator computation via ta library, handling insufficient data and NaN gracefully**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-08T16:10:16Z
- **Completed:** 2026-03-08T16:13:28Z
- **Tasks:** 2 (TDD RED + GREEN)
- **Files modified:** 2

## Accomplishments
- `fetch_daily_bars()` batches symbols (default 20), uses `Adjustment.SPLIT`, omits limit parameter to avoid per-symbol truncation
- `compute_indicators()` computes price, avg_volume, RSI(14), SMA(200), and above_sma200 with proper None handling for insufficient data
- 14 unit tests covering indicator math, edge cases (insufficient bars, NaN conversion), and batched bar fetching with mocked Alpaca client

## Task Commits

Each task was committed atomically:

1. **RED: Failing tests for market data** - `118bf8a` (test)
2. **GREEN: Implementation + test fixes** - `4f299bf` (feat)

_TDD plan: RED wrote all 14 tests (import error), GREEN implemented module and fixed test date generation._

## Files Created/Modified
- `screener/market_data.py` - Alpaca bar fetching and technical indicator computation (fetch_daily_bars, compute_indicators)
- `tests/test_market_data.py` - 14 unit tests: 9 for compute_indicators, 5 for fetch_daily_bars

## Decisions Made
- Used `pd.bdate_range(end="2026-03-06", periods=n)` instead of `pd.date_range(end=datetime.now(), periods=n, freq="B")` in tests to avoid off-by-one business-day alignment when `datetime.now()` falls on a weekend
- Minimum bar thresholds: 30 for RSI(14), 200 for SMA(200) -- returns None below threshold rather than computing unreliable values

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test date generation causing length mismatch**
- **Found during:** GREEN phase (first test run)
- **Issue:** `pd.date_range(end=datetime.now(), periods=50, freq="B")` generated 49 business dates when current day is Sunday, causing `ValueError: Length of values (50) does not match length of index (49)`
- **Fix:** Switched to `pd.bdate_range(end="2026-03-06", periods=n)` with a fixed weekday end date for deterministic test behavior
- **Files modified:** `tests/test_market_data.py`
- **Verification:** All 14 tests pass consistently
- **Committed in:** `4f299bf` (part of GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Test reliability fix -- no scope creep.

## Issues Encountered
- Pre-existing failures in `tests/test_finnhub_client.py` (4 tests from plan 02-01) due to `finnhub` module mocking issue where `FinnhubAPIException` becomes a MagicMock instead of a real exception class. Logged to `deferred-items.md` -- out of scope for this plan.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `fetch_daily_bars` and `compute_indicators` ready for Phase 3 screening pipeline integration
- Functions return dict format compatible with `ScreenedStock` field population
- Pre-existing finnhub test failures should be addressed before Phase 3

## Self-Check: PASSED

All files verified present, all commits verified in git history.

---
*Phase: 02-data-sources*
*Completed: 2026-03-08*
