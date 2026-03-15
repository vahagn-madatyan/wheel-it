---
estimated_steps: 6
estimated_files: 2
---

# T01: PutRecommendation dataclass and annualized return math

**Slice:** S01 — Put Screener Module
**Milestone:** M003

## Description

Create the foundation types for the put screener: the `PutRecommendation` dataclass and `compute_put_annualized_return()` function. These mirror `CallRecommendation` and `compute_call_annualized_return()` from `screener/call_screener.py`.

## Steps

1. Read `screener/call_screener.py` lines 1–80 to confirm the `CallRecommendation` and `compute_call_annualized_return` patterns.
2. Create `screener/put_screener.py` with module docstring, imports, and module constants `_PUT_DTE_MIN = 14`, `_PUT_DTE_MAX = 60`.
3. Implement `PutRecommendation` dataclass with fields: `symbol` (str), `underlying` (str), `strike` (float), `dte` (int), `premium` (float), `delta` (Optional[float]), `oi` (int), `spread` (float), `annualized_return` (float).
4. Implement `compute_put_annualized_return(premium, strike, dte)` → `Optional[float]`. Formula: `round((premium / strike) * (365 / dte) * 100, 2)`. Return None for zero strike, zero DTE, negative premium.
5. Create `tests/test_put_screener.py` with tests: annualized return math correctness (known values), zero strike → None, zero DTE → None, negative premium → None, large premium/strike → correct rounding, dataclass construction.
6. Run `python -m pytest tests/test_put_screener.py -v` to verify.

## Must-Haves

- [ ] `PutRecommendation` dataclass is importable from `screener.put_screener`
- [ ] `compute_put_annualized_return(1.50, 150.0, 30)` returns `12.17` (verified by test)
- [ ] `compute_put_annualized_return(0, 150.0, 30)` returns `0.0` (zero premium is valid, not invalid)
- [ ] `compute_put_annualized_return(1.50, 0, 30)` returns `None`
- [ ] `compute_put_annualized_return(1.50, 150.0, 0)` returns `None`
- [ ] `compute_put_annualized_return(-1.0, 150.0, 30)` returns `None`
- [ ] 10+ tests pass

## Verification

- `python -m pytest tests/test_put_screener.py -v` — all pass
- `python -m pytest tests/ -q` — 368+ existing tests still pass

## Inputs

- `screener/call_screener.py` — template for dataclass and math function patterns

## Expected Output

- `screener/put_screener.py` — module with `PutRecommendation`, `compute_put_annualized_return`, DTE constants
- `tests/test_put_screener.py` — 10+ tests for math and dataclass
