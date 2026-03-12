# S08: HV Rank + Earnings Calendar — UAT

**Milestone:** M001
**Written:** 2026-03-11

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S08 adds pure computation functions and filter logic with no external service dependencies at test time. All 47 tests use mocked Finnhub responses and synthetic bar data. The computation math and filter boundary logic are fully deterministic and verifiable through unit tests alone. Live runtime verification (Finnhub API calls) is deferred to S09 integration testing.

## Preconditions

- Python 3.13 venv activated (`source .venv/bin/activate`)
- `uv pip install -e .` completed successfully
- All test dependencies installed

## Smoke Test

Run `python -m pytest tests/test_hv_earnings.py -q` — should show 47 passed, 0 failed.

## Test Cases

### 1. HV Percentile Computation

1. Run `python -m pytest tests/test_hv_earnings.py::TestComputeHvPercentile -v`
2. **Expected:** 7 tests pass. Covers: result range [0,100], None on insufficient data, high-vol spike → high percentile, low-vol → low percentile, custom params, rounding.

### 2. HV Percentile Filter

1. Run `python -m pytest tests/test_hv_earnings.py::TestFilterHvPercentile -v`
2. **Expected:** 6 tests pass. Covers: above threshold → pass, below → fail, exact boundary → pass, None → neutral pass, aggressive/conservative threshold behavior.

### 3. Earnings Proximity Filter

1. Run `python -m pytest tests/test_hv_earnings.py::TestFilterEarningsProximity -v`
2. **Expected:** 8 tests pass. Covers: None → pass, within window → fail, outside → pass, exact boundary → fail (inclusive), one day past → pass, today → fail, preset-specific windows.

### 4. FinnhubClient Earnings Methods

1. Run `python -m pytest tests/test_hv_earnings.py::TestFinnhubEarnings -v`
2. **Expected:** 5 tests pass. Covers: calendar returns list, empty on failure, earnings_for_symbol returns date, None on no data, None on error.

### 5. Preset YAML Thresholds

1. Run `python -m pytest tests/test_hv_earnings.py::TestPresetsS08 -v`
2. **Expected:** 8 tests pass. Verifies hv_percentile_min (50/30/20) and earnings_exclusion_days (21/14/7) are set correctly in each preset YAML and that values are differentiated across presets.

### 6. Full Test Suite Regression

1. Run `python -m pytest tests/ -q`
2. **Expected:** 244 passed, 0 failed. No regressions in existing pipeline, display, config, or CLI tests.

## Edge Cases

### Insufficient Bar Data for HV Percentile

1. `compute_hv_percentile()` with fewer than 253 bars returns None
2. **Expected:** Stock passes `filter_hv_percentile` with neutral score (consistent with FIX-03 None handling)

### Earnings on Exact Boundary Day

1. `filter_earnings_proximity()` with `days_to_earnings == earnings_exclusion_days`
2. **Expected:** Filter fails (boundary is inclusive — selling into earnings day is still risky)

### No Earnings Data Available

1. `earnings_for_symbol()` returns None (Finnhub has no data for symbol)
2. **Expected:** `filter_earnings_proximity` passes with neutral score — absence of data should not eliminate a stock

### Finnhub API Error During Earnings Fetch

1. `earnings_for_symbol()` raises Exception internally
2. **Expected:** Returns None (caught internally), stock passes earnings filter with neutral score

## Failure Signals

- Any of the 47 new tests failing in `test_hv_earnings.py`
- Any of the 197 existing tests failing (regression)
- `compute_hv_percentile` returning values outside [0, 100]
- `filter_earnings_proximity` passing stocks with earnings today
- Missing `hv_percentile_min` or `earnings_exclusion_days` from any preset YAML
- `HV%ile` column missing from display table structure

## Requirements Proved By This UAT

- HVPR-01 — 7 computation tests + 2 Stage 1 integration tests prove HV percentile computation and filtering works with 30-day/252-day params
- HVPR-02 — 3 preset tests + 1 differentiation test prove per-preset threshold configuration
- HVPR-03 — Display test pass + table column addition prove HV%ile appears in results
- EARN-01 — 8 filter tests prove earnings proximity exclusion with configurable threshold
- EARN-02 — 5 FinnhubClient tests prove earnings calendar API integration (mocked)
- EARN-03 — 3 preset tests + 1 differentiation test prove per-preset earnings threshold configuration

## Not Proven By This UAT

- Live Finnhub earnings calendar API behavior (rate limits, data gaps for small-cap stocks)
- Live pipeline end-to-end with real earnings data (deferred to S09 integration testing)
- Screener performance impact of per-symbol earnings API calls on large universes
- Visual verification of HV%ile column rendering in terminal (artifact-driven only)

## Notes for Tester

- All tests use mocked API responses — no Finnhub API key required
- The 5 fixed stale tests in `test_screener_config.py` were inherited bugs from S07's preset overhaul
- `compute_hv_percentile` uses `np.random.seed(42)` in tests for deterministic synthetic data
