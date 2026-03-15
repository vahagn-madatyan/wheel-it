---
id: T01
parent: S01
milestone: M003
provides:
  - PutRecommendation dataclass with 9 fields (symbol, underlying, strike, dte, premium, delta, oi, spread, annualized_return)
  - compute_put_annualized_return(premium, strike, dte) → Optional[float]
  - DTE range constants _PUT_DTE_MIN=14, _PUT_DTE_MAX=60
  - 17 passing tests covering math, edge cases, dataclass construction, DTE constants
key_files:
  - screener/put_screener.py
  - tests/test_put_screener.py
key_decisions:
  - "D046 applied: annualized return uses premium/strike (not premium/cost_basis) because capital at risk for puts is strike×100"
patterns_established:
  - "PutRecommendation mirrors CallRecommendation — same structural pattern, different denominator in return formula"
drill_down_paths:
  - .gsd/milestones/M003/slices/S01/tasks/T01-plan.md
duration: 15min
verification_result: pass
completed_at: 2026-03-15T09:20:00Z
---

# T01: PutRecommendation dataclass and annualized return math

**PutRecommendation dataclass and compute_put_annualized_return() with (premium/strike)×(365/dte)×100 formula, 17 tests all passing**

## What Happened

Created `screener/put_screener.py` mirroring the `call_screener.py` structural pattern. The `PutRecommendation` dataclass has 9 fields (no `cost_basis` field since puts don't have one — the capital at risk is strike×100). The `compute_put_annualized_return()` function uses `premium/strike` as the denominator (D046), unlike calls which use `premium/cost_basis`. Edge cases (zero strike, zero DTE, negative premium) return None; zero premium returns 0.0.

## Deviations
None.

## Files Created/Modified
- `screener/put_screener.py` — New module with PutRecommendation, compute_put_annualized_return, DTE constants
- `tests/test_put_screener.py` — 17 tests: 3 dataclass, 12 math, 2 DTE constants
