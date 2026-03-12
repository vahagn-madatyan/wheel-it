---
id: T02
parent: S07
milestone: M001
provides:
  - Stage 2 filters (market_cap, debt_equity, net_margin, sales_growth, sector) return passed=True with neutral reason when metric is None
  - run_stage_2_filters no-profile case passes 5 Finnhub-dependent filters with neutral scores
  - Stocks with missing Finnhub data now reach scoring where compute_wheel_score gives neutral 0.5
key_files:
  - screener/pipeline.py
  - tests/test_pipeline.py
key_decisions:
  - None — followed plan exactly
patterns_established:
  - "No data — passing with neutral score" reason text on FilterResult indicates a neutral pass due to missing data
observability_surfaces:
  - FilterResult.reason shows "No data — passing with neutral score" for None metrics; "No Finnhub data — passing with neutral score" for no-profile case — visible in filter breakdown display
duration: 10m
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---

# T02: Fix None-handling in Stage 2 filters and update tests

**Stage 2 filters now return passed=True with neutral score when Finnhub metrics are None, letting stocks with patchy data reach scoring.**

## What Happened

Changed 5 Stage 2 filter functions (`filter_market_cap`, `filter_debt_equity`, `filter_net_margin`, `filter_sales_growth`, `filter_sector`) to return `passed=True` with reason `"No data — passing with neutral score"` when their respective metric is `None`. Updated the `run_stage_2_filters` no-profile fallback to pass all 5 Finnhub-dependent filters with `passed=True` and reason `"No Finnhub data — passing with neutral score"` (previously failed them all). Stage 1 filters (price, volume, RSI, SMA200) remain unchanged — they still return `passed=False` on `None` because missing bar data means the stock genuinely can't be screened. Updated 5 corresponding test assertions to match the new behavior. `filter_optionable` in the no-profile block was left as-is (it uses Alpaca data, not Finnhub).

## Verification

- `pytest tests/test_pipeline.py -v` — **63/63 passed** (same count as baseline, 5 assertions flipped)
- `pytest tests/test_pipeline.py -v -k "none"` — **12/12 passed** (all None-related tests)
- Manual review confirmed Stage 1 `test_price_none_fails`, `test_volume_none_fails`, `test_rsi_none_fails`, `test_sma200_none_fails` still assert `passed is False`

### Slice-level verification (partial — this is task 2 of 3):
- ✅ `pytest tests/test_pipeline.py -v` — all tests pass including updated None-handling assertions
- ⏳ `run-screener --preset moderate` — not yet runnable (preset overhaul in T03)
- ⏳ Three presets produce different result counts — presets not yet differentiated (T03)
- ⏳ D/E normalization debug log — not yet implemented (T03)

## Diagnostics

- `FilterResult.reason` text on each `ScreenedStock` shows `"No data — passing with neutral score"` when a Stage 2 metric is `None`
- In the no-profile path, reason is `"No Finnhub data — passing with neutral score"`
- Inspect via `stock.filter_results` — any entry with `passed=True` and `actual_value is None` indicates a neutral pass

## Deviations

None — followed plan exactly.

## Known Issues

None.

## Files Created/Modified

- `screener/pipeline.py` — Changed 5 Stage 2 filter None-branches from `passed=False` to `passed=True` with neutral reason; updated `run_stage_2_filters` no-profile block from fail-all to pass-with-neutral
- `tests/test_pipeline.py` — Flipped 5 test assertions: `passed is False` → `passed is True`, `"unavailable"` → `"no data"`
