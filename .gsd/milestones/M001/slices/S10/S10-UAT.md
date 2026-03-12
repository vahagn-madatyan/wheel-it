# S10: Covered Call Screening + Strategy Integration — UAT

**Milestone:** M001
**Written:** 2026-03-11

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All call screener logic is pure functions (fetch → filter → rank) tested with mocked API responses. The same Alpaca API patterns were validated live in S09's options chain work. No new API integrations or data shapes — only new composition of existing patterns.

## Preconditions

- `uv pip install -e .` completed successfully
- `.env` file with `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `IS_PAPER=true` (for live testing only)
- All 345 tests pass: `python -m pytest tests/ -q`

## Smoke Test

Run `python -m pytest tests/test_call_screener.py -q` — expect 43 passed, 0 failures.

## Test Cases

### 1. Annualized Return Math

1. Run `python -m pytest tests/test_call_screener.py::TestComputeCallAnnualizedReturn -v`
2. **Expected:** 8 tests pass — basic, low, high premium scenarios plus edge cases (zero/negative inputs return None)

### 2. Strike ≥ Cost Basis Enforcement

1. Run `python -m pytest tests/test_call_screener.py::TestScreenCalls::test_strike_below_cost_basis_excluded tests/test_call_screener.py::TestScreenCalls::test_strike_equal_to_cost_basis_included tests/test_call_screener.py::TestScreenCalls::test_all_below_cost_basis_returns_empty -v`
2. **Expected:** 3 tests pass — contracts below cost basis excluded, equal included, all-below returns empty

### 3. OI/Spread/Delta Filters

1. Run `python -m pytest tests/test_call_screener.py::TestScreenCalls -k "oi or spread or delta" -v`
2. **Expected:** 5 tests pass — low OI excluded, wide spread excluded, delta out-of-range excluded, no-greeks passes

### 4. Ranking by Annualized Return

1. Run `python -m pytest tests/test_call_screener.py::TestScreenCalls::test_sorted_by_annualized_return_descending -v`
2. **Expected:** Results sorted best-first by annualized return

### 5. Rich Table Output

1. Run `python -m pytest tests/test_call_screener.py::TestRenderCallResultsTable -v`
2. **Expected:** 4 tests pass — data renders with all columns, empty shows message, N/A for missing delta, multiple rows

### 6. CLI Entry Point

1. Run `python -m pytest tests/test_call_screener.py::TestRunCallScreenerCLI -v`
2. **Expected:** 3 tests pass — CLI invokes screen_calls, uppercases symbol, accepts preset override

### 7. Strategy Integration

1. Run `python -m pytest tests/test_call_screener.py::TestStrategyIntegration -v`
2. **Expected:** 3 tests pass — long_shares triggers call screener, empty results skips sell, insufficient shares skips screening

### 8. Preset Differentiation

1. Run `python -m pytest tests/test_call_screener.py::TestPresetThresholdsForCalls -v`
2. **Expected:** 5 tests pass — three presets have correct OI/spread thresholds, conservative rejects what moderate accepts

## Edge Cases

### API Failure During Contract Fetch

1. `test_api_exception_returns_empty` — API exception returns empty list, no crash
2. **Expected:** Graceful degradation, empty recommendations

### API Failure During Snapshot Fetch

1. `test_snapshot_fetch_exception_returns_empty` — Snapshot error returns empty list
2. **Expected:** Graceful degradation, empty recommendations

### No Snapshot for Contract

1. `test_missing_snapshot_for_contract_skipped` — Contract with no snapshot data is skipped
2. **Expected:** Other contracts still processed

### Zero Bid Price

1. `test_zero_bid_excluded` — Contract with $0 bid excluded (illiquid)
2. **Expected:** Not included in recommendations

### Snapshot Batching

1. `test_batching_over_100_contracts` — 150 contracts batched into 2 API calls
2. **Expected:** All contracts processed, 2 snapshot calls made

## Failure Signals

- Any test failure in `test_call_screener.py`
- `run-call-screener --help` not found after `uv pip install -e .`
- `run-strategy` crashing when encountering `long_shares` state (should use call screener gracefully)
- Regression in existing 302 tests

## Requirements Proved By This UAT

- CALL-01 — CLI tests prove standalone `run-call-screener` works
- CALL-02 — `test_basic_screening_returns_recommendation` proves symbol + cost basis acceptance
- CALL-03 — 3 strike/cost-basis tests prove enforcement
- CALL-04 — 6 filter tests prove DTE/OI/spread/delta filtering with preset thresholds
- CALL-05 — Rich table test proves all required columns present
- CALL-06 — 3 strategy integration tests prove `run-strategy` uses call screener for assigned positions

## Not Proven By This UAT

- Live Alpaca API call contract fetching (tested via mocks; live patterns validated in S09)
- Actual order placement via Alpaca (mock-verified; live trading is operational concern)
- Real-time delta accuracy from Alpaca greeks endpoint (depends on market hours and data provider)

## Notes for Tester

- All tests use mocked Alpaca clients — no live API calls needed to verify.
- The `run-call-screener` CLI requires valid Alpaca credentials to actually execute against live data, but the test suite validates all logic without them.
- The strategy integration test (`TestStrategyIntegration`) patches heavily to isolate the call screener invocation — this is expected given the number of dependencies in `run_strategy.py`.
