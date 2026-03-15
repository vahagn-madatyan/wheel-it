# S01: Put Screener Module

**Goal:** Build `screener/put_screener.py` mirroring the call screener pattern — multi-symbol contract fetching with pagination, buying power pre-filter, OI/spread/delta filters, one-per-underlying selection, annualized return ranking, and Rich table display.
**Demo:** `screen_puts(trade_client, option_client, ["AAPL", "MSFT"], 50000.0, config)` returns ranked `PutRecommendation` objects verified by 40+ tests.

## Must-Haves

- `PutRecommendation` dataclass with: symbol, underlying, strike, dte, premium, delta, oi, spread, annualized_return
- `compute_put_annualized_return(premium, strike, dte)` returns `(premium / strike) * (365 / dte) * 100` or None for invalid inputs
- `screen_puts()` accepts `(trade_client, option_client, symbols, buying_power, config?)` and returns `list[PutRecommendation]`
- Buying power pre-filter: symbols where `100 * latest_price > buying_power` are excluded before contract fetch
- Multi-symbol contract fetch with pagination (1000 per page, uses `next_page_token`)
- OI pre-filter from contract data before snapshot fetch (same as call screener)
- Spread filter: `(ask - bid) / midpoint` where midpoint = `(bid + ask) / 2` (D034)
- Delta filter: `abs(delta)` between `DELTA_MIN` and `DELTA_MAX`; None-delta contracts pass (D039)
- One-per-underlying: after scoring, keep only the best contract per underlying symbol
- DTE range: 14–60 days (module constants, matching D032)
- Results sorted by annualized return descending
- `render_put_results_table()` displays Rich table
- 40+ tests covering all logic

## Verification

- `python -m pytest tests/test_put_screener.py -v` — all tests pass
- `python -m pytest tests/ -q` — 368+ existing tests still pass (zero regressions)

## Observability / Diagnostics

- Runtime signals: `screen_puts()` logs contract count, recommendation count, symbols excluded by buying power
- Inspection surfaces: test suite with fine-grained assertions
- Failure visibility: empty recommendation list with debug-level log explaining why (no contracts, all filtered, etc.)

## Tasks

- [x] **T01: PutRecommendation dataclass and annualized return math** `est:30m`
  - Why: Foundation types and math — everything else builds on these
  - Files: `screener/put_screener.py`, `tests/test_put_screener.py`
  - Do: Create `PutRecommendation` dataclass mirroring `CallRecommendation`. Implement `compute_put_annualized_return(premium, strike, dte)` with formula `(premium / strike) * (365 / dte) * 100`. Handle edge cases: zero strike, zero DTE, negative premium → return None. Write 10+ tests: math correctness, edge cases, dataclass construction.
  - Verify: `python -m pytest tests/test_put_screener.py -v`
  - Done when: `PutRecommendation` is importable and `compute_put_annualized_return` passes all math tests

- [x] **T02: Core screen_puts() with buying power pre-filter and contract fetch** `est:1h`
  - Why: The core screening pipeline — fetches contracts for multiple symbols with pagination and pre-filters by buying power
  - Files: `screener/put_screener.py`, `tests/test_put_screener.py`
  - Do: Implement `screen_puts(trade_client, option_client, symbols, buying_power, config?)`. Step 1: fetch latest trades via `trade_client.get_stock_latest_trade()`, exclude symbols where `100 * price > buying_power`. Step 2: fetch PUT contracts in DTE 14–60 with pagination (loop on `next_page_token`, 1000 per page). Step 3: OI pre-filter. Step 4: batch snapshots (100 per batch). Step 5: spread/delta filter. Step 6: compute annualized return. Step 7: one-per-underlying selection (keep best per underlying). Step 8: sort by annualized return descending. Use `ScreenerConfig()` defaults when config is None. Write 20+ tests: buying power pre-filter, pagination, OI filter, spread filter, delta filter (including None-delta pass), one-per-underlying, empty results, API failure handling.
  - Verify: `python -m pytest tests/test_put_screener.py -v`
  - Done when: `screen_puts()` returns correctly filtered and ranked `PutRecommendation` list with all edge cases tested

- [x] **T03: Rich table display and preset threshold tests** `est:30m`
  - Why: Completes the module with display capability and preset configurability verification
  - Files: `screener/put_screener.py`, `tests/test_put_screener.py`
  - Do: Implement `render_put_results_table(recommendations, buying_power, console?)` with columns: #, Symbol, Underlying, Strike, DTE, Premium, Delta, OI, Spread, Ann. Return. Handle empty list with yellow message. Add tests for: table renders with data (all columns present), empty results message, preset threshold application (conservative vs moderate vs aggressive OI/spread thresholds), DTE range constants match call screener.
  - Verify: `python -m pytest tests/test_put_screener.py -v && python -m pytest tests/ -q`
  - Done when: Rich table renders correctly and all preset thresholds are verified in tests

## Files Likely Touched

- `screener/put_screener.py` (new)
- `tests/test_put_screener.py` (new)
