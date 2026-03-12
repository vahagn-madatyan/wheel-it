---
id: S02
parent: M001
milestone: M001
provides:
  - "FinnhubClient class with rate-limited API access"
  - "METRIC_FALLBACK_CHAINS constant for resilient metric extraction"
  - "extract_metric() helper for Finnhub metric key resolution"
  - "fetch_daily_bars() for batched Alpaca bar retrieval with split adjustment"
  - "compute_indicators() for RSI(14), SMA(200), price, avg_volume, above_sma200"
requires: []
affects: []
key_files: []
key_decisions:
  - "Used lambda wrappers in company_profile/company_metrics to cleanly separate SDK kwargs from logging kwargs in _call_with_retry"
  - "FinnhubAPIException mock requires preserving the real exception class when patching the finnhub module, preventing TypeError on except clauses"
  - "Used pd.bdate_range with fixed end date in tests instead of datetime.now() to avoid non-deterministic business-day alignment issues"
  - "Minimum 30 bars required for RSI(14) computation, 200 bars for SMA(200) -- below threshold returns None"
patterns_established:
  - "FinnhubClient rate limiting: time.monotonic()-based throttle with configurable call_interval (default 1.1s)"
  - "429 retry pattern: single retry after 5s backoff, second failure propagates to caller"
  - "Metric fallback chains: ordered list of alternate Finnhub key names per metric, first non-None wins"
  - "NaN-to-None: Always check pd.isna() before returning ta library outputs to prevent float NaN from leaking into ScreenedStock fields"
  - "Batched bar fetching: No limit parameter on multi-symbol StockBarsRequest to avoid total-across-symbols truncation"
observability_surfaces: []
drill_down_paths: []
duration: 3min
verification_result: passed
completed_at: 2026-03-08
blocker_discovered: false
---
# S02: Data Sources

**# Phase 2 Plan 1: FinnhubClient Summary**

## What Happened

# Phase 2 Plan 1: FinnhubClient Summary

**Rate-limited Finnhub API client with 429 retry logic and metric fallback chains for resilient fundamental data fetching**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-08T16:10:21Z
- **Completed:** 2026-03-08T16:15:00Z
- **Tasks:** 3 (setup + TDD RED + TDD GREEN)
- **Files modified:** 3

## Accomplishments
- FinnhubClient with 1.1s sleep-based throttle maintaining ~54 calls/min (under 60/min free tier)
- 429 error handling: one retry after 5s backoff, second 429 propagates to caller for skip logic
- Metric fallback chains for debt_equity, net_margin, and sales_growth with ordered key resolution
- 21 unit tests covering throttle, retry, exception handling, SDK delegation, fallback chains, and debug logging
- All 65 tests pass (44 existing + 21 new)

## Task Commits

Each task was committed atomically:

1. **Task 1: Setup -- add finnhub-python dependency** - `025bf84` (chore)
2. **Task 2: RED -- write failing tests** - `e7b771c` (test)
3. **Task 3: GREEN -- implement FinnhubClient** - `19cf2a1` (feat)

_TDD plan: RED phase wrote 21 failing tests, GREEN phase implemented module to pass all tests._

## Files Created/Modified
- `screener/finnhub_client.py` - FinnhubClient class with rate limiting, 429 retry, METRIC_FALLBACK_CHAINS, extract_metric()
- `tests/test_finnhub_client.py` - 21 unit tests covering all behaviors: throttle, retry, exception handling, fallback chains, logging
- `pyproject.toml` - Added finnhub-python to dependencies

## Decisions Made
- Used lambda wrappers in company_profile() and company_metrics() to bind SDK call arguments, keeping _call_with_retry() signature clean with separate symbol/endpoint logging parameters
- Tests must set `mock_finnhub.FinnhubAPIException = finnhub.FinnhubAPIException` when patching the entire finnhub module, because Python's `except` clause requires a real BaseException subclass (MagicMock causes TypeError)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed FinnhubAPIException mock in retry tests**
- **Found during:** Task 3 (GREEN phase)
- **Issue:** Patching `screener.finnhub_client.finnhub` replaced the entire module with MagicMock, causing `except finnhub.FinnhubAPIException` to throw TypeError ("catching classes that do not inherit from BaseException")
- **Fix:** Added `mock_finnhub.FinnhubAPIException = finnhub.FinnhubAPIException` in all tests that patch the finnhub module and need exception handling
- **Files modified:** tests/test_finnhub_client.py
- **Verification:** All 21 tests pass
- **Committed in:** 19cf2a1 (part of GREEN phase commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix in tests)
**Impact on plan:** Test mock fix was necessary for correct exception handling in mocked contexts. No scope creep.

## Issues Encountered
- The plan's RESEARCH.md pattern for `_call_with_retry` used overlapping keyword argument names (`symbol=` needed both for logging and for forwarding to `company_profile2`). Resolved by using lambda wrappers to pre-bind SDK arguments.

## User Setup Required
None - no external service configuration required. FINNHUB_API_KEY was already configured in Phase 1 Plan 2.

## Next Phase Readiness
- FinnhubClient ready for use by the screening pipeline (Plan 02-02 market data, Phase 3 pipeline)
- Rate limiting ensures safe sequential fetching of 200+ symbols
- Metric fallback chains handle undocumented Finnhub key naming variations

## Self-Check: PASSED

All files verified present, all commit hashes found in git log.

---
*Phase: 02-data-sources*
*Completed: 2026-03-08*

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
