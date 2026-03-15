---
id: T02
parent: S01
milestone: M003
provides:
  - screen_puts(trade_client, option_client, symbols, buying_power, config?, stock_client?) function
  - Multi-symbol contract fetch with pagination (next_page_token loop)
  - Buying power pre-filter via stock_client.get_stock_latest_trade()
  - OI/spread/delta filter pipeline matching call screener
  - One-per-underlying diversification selection
  - 26 screen_puts() tests covering all filter stages and edge cases
key_files:
  - screener/put_screener.py
  - tests/test_put_screener.py
key_decisions:
  - "Added stock_client parameter to screen_puts() — needed for buying power pre-filter; stock_client=None skips the filter (all symbols proceed)"
patterns_established:
  - "Multi-symbol put screening mirrors call screener filter pipeline but adds pagination, buying power pre-filter, and one-per-underlying selection"
drill_down_paths:
  - .gsd/milestones/M003/slices/S01/tasks/T02-plan.md
duration: 25min
verification_result: pass
completed_at: 2026-03-15T09:45:00Z
---

# T02: Core screen_puts() with buying power pre-filter and contract fetch

**screen_puts() with multi-symbol pagination, buying power pre-filter via stock_client, OI/spread/delta filters, one-per-underlying selection, 26 tests all passing**

## What Happened

Built the core `screen_puts()` function following the call screener pattern but extended for multi-symbol use. Key additions: (1) buying power pre-filter fetches latest stock prices via `stock_client` and excludes symbols where `100 × price > buying_power`, (2) contract fetch uses pagination loop on `next_page_token` for large multi-symbol results, (3) one-per-underlying selection keeps only the highest annualized return per underlying after all filters.

The function signature includes `stock_client=None` as an optional parameter — when None, the buying power pre-filter is skipped and all symbols proceed directly to contract fetch. This supports callers who don't have a stock client or want to skip the pre-filter.

## Deviations
Added `stock_client` as an optional parameter not in the original boundary map. This was necessary because `get_stock_latest_trade()` lives on `StockHistoricalDataClient`, not on `TradingClient` or `OptionHistoricalDataClient`. The boundary map should be updated to reflect this.

## Files Created/Modified
- `screener/put_screener.py` — Added `screen_puts()` function (~130 lines)
- `tests/test_put_screener.py` — Extended from 17 to 43 tests (26 new screen_puts tests)
