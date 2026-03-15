---
estimated_steps: 9
estimated_files: 2
---

# T02: Core screen_puts() with buying power pre-filter and contract fetch

**Slice:** S01 — Put Screener Module
**Milestone:** M003

## Description

Build the core `screen_puts()` function that fetches PUT contracts for multiple symbols, pre-filters by buying power, applies OI/spread/delta filters, enforces one-per-underlying diversification, and returns ranked `PutRecommendation` objects. This is the most complex task in the slice — it handles multi-symbol pagination, buying power pre-filtering, and all filter stages.

## Steps

1. Read `screener/call_screener.py` `screen_calls()` (lines 82–200) to confirm the single-symbol pipeline pattern.
2. Read `core/broker_client.py` `get_options_contracts()` (lines 70–95) to understand pagination pattern.
3. Implement buying power pre-filter: call `trade_client.get_stock_latest_trade()` for all symbols, filter to symbols where `100 * price <= buying_power`. Handle API failure gracefully (log and skip symbol, don't crash).
4. Implement multi-symbol contract fetch: `GetOptionContractsRequest` with `underlying_symbols` list, `ContractType.PUT`, `AssetStatus.ACTIVE`, DTE range 14–60, limit=1000. Loop on `next_page_token` for pagination.
5. Implement OI pre-filter: filter contracts by `open_interest >= oi_min` from config.
6. Implement snapshot batch fetch: 100 per batch using `OptionSnapshotRequest`, same pattern as call screener.
7. Implement spread filter (D034), delta filter with None-delta pass-through (D039), and annualized return computation.
8. Implement one-per-underlying selection: group by underlying, keep the contract with highest annualized return per group. Sort final list by annualized return descending.
9. Write 25+ tests covering: buying power pre-filter (affordable/unaffordable/all unaffordable), multi-symbol returns from multiple underlyings, pagination (mock `next_page_token`), OI filter, spread filter, delta filter (including None pass), one-per-underlying (two contracts same underlying keeps best), empty symbols list, API failure graceful handling, config defaults when None, preset threshold application.

## Must-Haves

- [ ] Symbols where `100 * price > buying_power` are excluded before contract fetch
- [ ] Contracts are fetched with pagination (handles `next_page_token`)
- [ ] OI pre-filter runs before snapshot fetch (API call savings)
- [ ] Spread filter uses `(ask - bid) / midpoint` formula (D034)
- [ ] None-delta contracts pass the delta filter (D039)
- [ ] Only one recommendation per underlying symbol (best annualized return wins)
- [ ] Results sorted by annualized return descending
- [ ] API failure in `get_stock_latest_trade()` returns empty list, not crash
- [ ] `screen_puts()` works with `config=None` (uses ScreenerConfig defaults)
- [ ] 25+ tests pass

## Verification

- `python -m pytest tests/test_put_screener.py -v` — all pass
- `python -m pytest tests/ -q` — 368+ existing tests still pass

## Observability Impact

- Signals added: `screen_puts()` logs buying power filter results, contract count, final recommendation count
- How a future agent inspects: run tests or read log output at DEBUG level
- Failure state exposed: empty list returned with debug logs explaining filter stage where all candidates were eliminated

## Inputs

- `screener/put_screener.py` — T01's `PutRecommendation` and `compute_put_annualized_return()`
- `screener/call_screener.py` — template for filter pipeline
- `core/broker_client.py` — pagination pattern reference

## Expected Output

- `screener/put_screener.py` — complete `screen_puts()` function
- `tests/test_put_screener.py` — extended to 35+ tests total
