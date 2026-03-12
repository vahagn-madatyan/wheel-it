---
id: T01
parent: S02
milestone: M001
provides:
  - "FinnhubClient class with rate-limited API access"
  - "METRIC_FALLBACK_CHAINS constant for resilient metric extraction"
  - "extract_metric() helper for Finnhub metric key resolution"
requires: []
affects: []
key_files: []
key_decisions: []
patterns_established: []
observability_surfaces: []
drill_down_paths: []
duration: 4min
verification_result: passed
completed_at: 2026-03-08
blocker_discovered: false
---
# T01: 02-data-sources 01

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
