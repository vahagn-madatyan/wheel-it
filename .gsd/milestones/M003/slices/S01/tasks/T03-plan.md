---
estimated_steps: 5
estimated_files: 2
---

# T03: Rich table display and preset threshold tests

**Slice:** S01 — Put Screener Module
**Milestone:** M003

## Description

Add `render_put_results_table()` for Rich table output and write tests verifying that preset thresholds (conservative/moderate/aggressive OI and spread) correctly influence filtering. This completes the S01 module.

## Steps

1. Implement `render_put_results_table(recommendations, buying_power, console?)` in `screener/put_screener.py`. Columns: #, Symbol, Underlying, Strike, DTE, Premium, Delta, OI, Spread, Ann. Return. Green styling on annualized return. Empty list shows yellow message. Console injection pattern for testability (D015).
2. Write display tests: table renders with data (verify all column headers), multiple rows render, empty list shows message, delta=None shows "N/A".
3. Write preset threshold tests: conservative config (OI 500, spread 0.05) rejects a contract that moderate (OI 100, spread 0.10) would accept. Verify DTE constants `_PUT_DTE_MIN == 14` and `_PUT_DTE_MAX == 60`.
4. Write a test confirming `screen_puts()` returns at most one recommendation per underlying when given multiple contracts for the same symbol.
5. Run full test suite to confirm zero regressions.

## Must-Haves

- [ ] `render_put_results_table()` shows columns: #, Symbol, Underlying, Strike, DTE, Premium, Delta, OI, Spread, Ann. Return
- [ ] Empty recommendations shows yellow "No put recommendations" message
- [ ] Conservative OI/spread thresholds are stricter than moderate (verified by test)
- [ ] DTE constants match call screener: `_PUT_DTE_MIN == 14`, `_PUT_DTE_MAX == 60`
- [ ] 40+ total tests in `test_put_screener.py`

## Verification

- `python -m pytest tests/test_put_screener.py -v` — 40+ tests pass
- `python -m pytest tests/ -q` — all 368+ tests pass

## Inputs

- `screener/put_screener.py` — T01 and T02's types and `screen_puts()` function
- `tests/test_call_screener.py` — display test patterns to follow

## Expected Output

- `screener/put_screener.py` — complete with `render_put_results_table()`
- `tests/test_put_screener.py` — 40+ tests total covering math, filtering, display, presets
