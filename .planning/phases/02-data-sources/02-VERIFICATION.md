---
phase: 02-data-sources
verified: 2026-03-08T18:00:00Z
status: passed
score: 12/12 must-haves verified
---

# Phase 2: Data Sources Verification Report

**Phase Goal:** The screener can fetch fundamental data from Finnhub and compute technical indicators from Alpaca bars, handling rate limits and missing data gracefully
**Verified:** 2026-03-08T18:00:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

**Plan 02-01 (FinnhubClient):**

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | Finnhub API calls are throttled to at most ~60 calls/min via sleep-based rate limiting | VERIFIED | `_throttle()` at line 75-80 uses `time.monotonic()` + `time.sleep(call_interval - elapsed)` with default `call_interval=1.1` (~54 calls/min). Tests `TestThrottle` verify sleep duration and no-sleep cases. |
| 2 | A 429 response triggers one retry after 5s backoff; a second 429 skips the symbol without crashing | VERIFIED | `_call_with_retry()` at lines 98-120 catches `FinnhubAPIException` with `status_code == 429`, sleeps 5s, retries once, re-raises on second failure. Tests `TestRetry429` verify both paths. |
| 3 | Missing/null metric values are resolved via fallback key chains | VERIFIED | `METRIC_FALLBACK_CHAINS` dict at lines 22-38 defines chains for debt_equity, net_margin, sales_growth. `extract_metric()` at lines 41-57 iterates chain keys, skips None values. Tests `TestExtractMetric` cover primary, fallback, all-missing, and None-value-skipped cases. |
| 4 | Completely empty Finnhub responses (symbol not found) are logged as WARNING and skipped | VERIFIED | `company_profile()` returns SDK response directly; empty dict `{}` is a valid passthrough (test `test_company_profile_empty_response` verifies). The 429 handling logs WARNING at line 107. |
| 5 | Each API call is logged at DEBUG level with symbol, endpoint, and response time | VERIFIED | `_call_with_retry()` at line 103 logs `"%s %s completed in %.2fs", symbol, endpoint, duration`. Test `TestDebugLogging::test_successful_call_logs_debug` verifies AAPL and profile2 appear in log. |

**Plan 02-02 (Market Data):**

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 6 | RSI(14) is computed correctly from Alpaca daily bar close prices using ta library | VERIFIED | `compute_indicators()` at line 90: `RSIIndicator(close=close, window=14).rsi()`. Tests verify RSI is float 0-100 with sufficient bars. |
| 7 | SMA(200) is computed correctly from Alpaca daily bar close prices using ta library | VERIFIED | `compute_indicators()` at line 98: `SMAIndicator(close=close, window=200).sma_indicator()`. Test with constant close=100.0 verifies SMA==100.0. |
| 8 | Symbols with fewer than 200 bars return sma_200=None and above_sma200=None | VERIFIED | Lines 107-109: `else: result["sma_200"] = None; result["above_sma200"] = None`. Test `test_sma_with_insufficient_bars` verifies with 150-bar DataFrame. |
| 9 | Symbols with fewer than 30 bars return rsi_14=None | VERIFIED | Lines 93-94: `else: result["rsi_14"] = None`. Test `test_rsi_with_insufficient_bars` verifies with 20-bar DataFrame. |
| 10 | NaN values from ta library are converted to None | VERIFIED | Lines 92 and 100: `None if pd.isna(val) else float(val)`. Test `test_nan_converted_to_none` verifies no float NaN leaks through. |
| 11 | Alpaca bars are fetched in batches of ~20 symbols with split adjustment and no limit parameter | VERIFIED | `fetch_daily_bars()` at lines 45-57: batch loop with `batch_size=20`, `Adjustment.SPLIT`, no `limit` param. Tests verify 3 calls for 25 symbols at batch_size=10, SPLIT adjustment, and limit is None. |
| 12 | Average daily volume is computed from the fetched bar data | VERIFIED | Line 85: `float(volume.mean())`. Test `test_avg_volume` verifies with known values. |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `screener/finnhub_client.py` | FinnhubClient class with rate limiting, retry, metric extraction | VERIFIED | 152 lines. Exports: FinnhubClient, METRIC_FALLBACK_CHAINS, extract_metric. |
| `tests/test_finnhub_client.py` | Unit tests (min 80 lines) | VERIFIED | 385 lines, 21 tests across 7 test classes. |
| `screener/market_data.py` | Bar fetching and indicator computation (min 50 lines) | VERIFIED | 111 lines. Exports: fetch_daily_bars, compute_indicators. |
| `tests/test_market_data.py` | Unit tests (min 60 lines) | VERIFIED | 216 lines, 14 tests across 2 test classes. |
| `pyproject.toml` | finnhub-python in dependencies | VERIFIED | Line 22: `"finnhub-python"` in dependencies list. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `screener/finnhub_client.py` | `config/credentials.py` | `require_finnhub_key()` | WIRED | Line 12: `from config.credentials import require_finnhub_key`. Used in `__init__` at line 70. |
| `screener/finnhub_client.py` | `finnhub.Client` | SDK wrapper | WIRED | Line 71: `self._client = finnhub.Client(api_key=self._key)`. Used via lambdas in company_profile/company_metrics. |
| `screener/market_data.py` | `ta.momentum.RSIIndicator` | RSI computation | WIRED | Line 16: `from ta.momentum import RSIIndicator`. Used at line 90: `RSIIndicator(close=close, window=14).rsi()`. |
| `screener/market_data.py` | `ta.trend.SMAIndicator` | SMA computation | WIRED | Line 17: `from ta.trend import SMAIndicator`. Used at line 98: `SMAIndicator(close=close, window=200).sma_indicator()`. |
| `screener/market_data.py` | `alpaca.data.requests.StockBarsRequest` | Bar data fetching | WIRED | Line 14: `from alpaca.data.requests import StockBarsRequest`. Used at line 50 with TimeFrame.Day, Adjustment.SPLIT. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| SAFE-02 | 02-01 | Finnhub API calls are rate-limited to respect 60 calls/min free tier limit | SATISFIED | `_throttle()` enforces 1.1s minimum interval (~54 calls/min). 429 retry logic with 5s backoff. 21 tests cover rate limiting and retry paths. |
| SAFE-04 | 02-01, 02-02 | Screener handles missing/null Finnhub metric values gracefully with fallback key chains | SATISFIED | `METRIC_FALLBACK_CHAINS` with 3 chains (debt_equity, net_margin, sales_growth). `extract_metric()` resolves via ordered key lookup. Market data handles insufficient bars and NaN-to-None conversion. |

No orphaned requirements found. REQUIREMENTS.md traceability table maps SAFE-02 and SAFE-04 to Phase 2, and both are claimed by the phase plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (none) | - | - | - | No TODO, FIXME, placeholder, or stub patterns found in any source file |

### Human Verification Required

### 1. Live Finnhub Rate Limiting

**Test:** Run FinnhubClient against the real Finnhub API with 60+ sequential calls and monitor for 429 responses.
**Expected:** All calls complete successfully with ~1.1s spacing; no 429 errors hit.
**Why human:** Rate limiting behavior depends on real network timing and Finnhub server-side rate counting. Unit tests mock time.sleep/time.monotonic.

### 2. Live Alpaca Bar Fetching

**Test:** Call `fetch_daily_bars()` with a list of 25 real symbols and verify returned DataFrames contain split-adjusted daily bars with close/volume columns.
**Expected:** Dict with ~25 entries, each a DataFrame with 200+ rows of daily bar data.
**Why human:** Requires live Alpaca API credentials and network access. Unit tests mock the StockHistoricalDataClient.

### 3. Deferred Items Resolution

**Test:** Review `deferred-items.md` which documents a pre-existing FinnhubAPIException mocking issue.
**Expected:** The issue appears to have been resolved (all 65 tests pass in full suite), but the deferred-items.md still documents it as open.
**Why human:** Confirm if deferred-items.md should be updated to reflect the fix, or if the issue is intermittent.

### Gaps Summary

No gaps found. All 12 observable truths are verified. All 5 artifacts exist, are substantive (well above minimum line counts), and are properly wired. All 5 key links are confirmed connected. Both requirement IDs (SAFE-02, SAFE-04) are satisfied with implementation evidence. No anti-patterns detected. All 35 phase tests and all 65 full suite tests pass. All 5 commit hashes from the summaries are verified in git history.

---

_Verified: 2026-03-08T18:00:00Z_
_Verifier: Claude (gsd-verifier)_
