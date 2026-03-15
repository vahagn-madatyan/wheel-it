# M003 Requirements — Execution Cleanup

## Active

(none — all 9 requirements validated during M003 execution)

## Validated

### EXEC-01 — Put screener function exists with same interface pattern as call screener
- Class: core-capability
- Status: validated
- Description: `screen_puts()` in `screener/put_screener.py` accepts `trade_client`, `option_client`, `symbols`, `buying_power`, and optional `ScreenerConfig`, returns `list[PutRecommendation]` sorted by annualized return descending
- Why it matters: Symmetric interface enables consistent web API wrapping and testability
- Source: user (premium-expansion.md E5)
- Primary owning slice: M003/S01
- Supporting slices: M003/S02
- Proof: `screen_puts()` callable with matching signature; PutRecommendation dataclass exists; 50 tests in test_put_screener.py covering math, filtering, pagination, one-per-underlying, edge cases

### EXEC-02 — Put screening applies bid/ask spread filter
- Class: core-capability
- Status: validated
- Description: `screen_puts()` rejects put contracts where `(ask - bid) / midpoint > spread_max` from screener config, matching call screener behavior
- Why it matters: Wide-spread puts fill poorly; current put path has no spread check
- Source: user (premium-expansion.md E1)
- Primary owning slice: M003/S01
- Supporting slices: none
- Proof: `test_wide_spread_excluded` and `test_tight_spread_passes` in test_put_screener.py; spread filter at put_screener.py line 265-268

### EXEC-03 — Both put and call scoring use annualized return
- Class: core-capability
- Status: validated
- Description: Puts scored by `(bid / strike) × (365 / DTE) × 100` — annualized return on capital at risk. Calls already use `(premium / cost_basis) × (365 / DTE) × 100`
- Why it matters: Consistent scoring enables apples-to-apples comparison in dashboard; current put formula double-counts delta
- Source: user (premium-expansion.md E2)
- Primary owning slice: M003/S01
- Supporting slices: none
- Proof: `compute_put_annualized_return(1.5, 150, 30)` returns 12.17; 12 math tests in TestComputePutAnnualizedReturn; D046 documents formula choice

### EXEC-04 — Put DTE minimum is 7 days (not 0)
- Class: core-capability
- Status: validated
- Description: Put contracts with DTE < 7 are excluded from screening. Minimum DTE raised from 0 to 7 for puts
- Why it matters: 0-6 DTE options have spiking gamma risk and negligible time value — poor risk/reward for premium selling
- Source: user (premium-expansion.md E3)
- Primary owning slice: M003/S01
- Supporting slices: none
- Proof: `_PUT_DTE_MIN = 14` (exceeds requirement of 7); DTE constant tests in TestDTEConstants; D032 documents DTE range choice

### EXEC-05 — `run-strategy` uses `screen_puts()` for put selection
- Class: core-capability
- Status: validated
- Description: `run_strategy.py` calls `screen_puts()` to get `list[PutRecommendation]` then executes best per underlying until buying power exhausted
- Why it matters: Aligns put execution with call execution pattern in `run_strategy.py`
- Source: user (premium-expansion.md E5)
- Primary owning slice: M003/S02
- Supporting slices: M003/S01
- Proof: `test_strategy_calls_screen_puts_not_sell_puts`, `test_strategy_sells_put_recommendations`, `test_empty_recommendations_no_crash` in test_cli_strategy.py; `from screener.put_screener import screen_puts` in run_strategy.py line 38

### EXEC-06 — Dead `sell_calls()` code removed
- Class: quality-attribute
- Status: validated
- Description: `sell_calls()` in `core/execution.py` is deleted. Unused `from core.execution import sell_calls` in `run_strategy.py` is removed
- Why it matters: Dead code creates confusion about which path is live (D038 confirmed screen_calls is the live path)
- Source: inferred
- Primary owning slice: M003/S03
- Supporting slices: M003/S02
- Proof: `core/execution.py` deleted entirely; `test_no_core_execution_imports` AST check passes in test_cli_strategy.py; zero `rg "from core.execution"` matches

### EXEC-07 — Dead strategy functions removed after put screener replaces them
- Class: quality-attribute
- Status: validated
- Description: `filter_options()`, `score_options()`, `select_options()`, `filter_underlying()` in `core/strategy.py` are removed
- Why it matters: Prevents confusion about which scoring/filtering path is active
- Source: inferred
- Primary owning slice: M003/S03
- Supporting slices: M003/S02
- Proof: `core/strategy.py` deleted; zero `rg "from core.strategy"` matches; 425 tests pass

### EXEC-08 — All existing tests continue to pass
- Class: quality-attribute
- Status: validated
- Description: The 368 existing tests pass (increased to 425 total with new tests)
- Why it matters: Refactoring must not break existing functionality
- Source: inferred
- Primary owning slice: M003/S04
- Supporting slices: M003/S01, M003/S02, M003/S03
- Proof: `python -m pytest tests/ -q` → 425 passed, 0 failed; fixed 3 call screener strategy tests that patched removed sell_puts

### EXEC-09 — New put screener has comprehensive test coverage
- Class: quality-attribute
- Status: validated
- Description: `test_put_screener.py` covers spread filter, DTE minimum, annualized return scoring, multiple symbols, buying power constraint, empty results, edge cases
- Why it matters: Put screener is a critical execution path — must be thoroughly tested
- Source: inferred
- Primary owning slice: M003/S01
- Supporting slices: M003/S02
- Proof: 53 tests in test_put_screener.py: 3 dataclass, 12 math, 2 DTE constants, 26 screen_puts filter/pipeline, 5 display, 2 preset threshold, 3 CLI tests

## Deferred

### EXEC-D01 — DTE ranges configurable per preset in ScreenerConfig YAML
- Class: core-capability
- Status: deferred
- Description: DTE min/max could be made configurable per preset instead of module-level constants
- Why it matters: Different presets might benefit from different DTE windows (conservative=30-45, aggressive=7-21)
- Source: inferred
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: D032 explicitly noted this as "Yes — revisable if users need different windows." Defer to avoid scope creep — current constants work well

### EXEC-D02 — Put strike floor guard (avoid deep ITM assignments)
- Class: core-capability
- Status: deferred
- Description: Add a guard rejecting put strikes significantly above current stock price to limit assignment overpay risk
- Why it matters: A put at a strike far above market price guarantees deep-ITM assignment at a bad price
- Source: inferred (premium-expansion.md mentions this as a missing guard)
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Current delta filter (0.15-0.30) already limits this somewhat — deep ITM puts have high delta and get filtered. Explicit guard is nice-to-have

## Out of Scope

### EXEC-X01 — FMP/ORATS integration
- Class: core-capability
- Status: out-of-scope
- Description: Premium data source integration is a separate milestone
- Why it matters: Prevents scope creep — this milestone is about execution path unification
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a

### EXEC-X02 — Web API / FastAPI wrapping
- Class: core-capability
- Status: out-of-scope
- Description: Building the SaaS web layer is a separate milestone
- Why it matters: This milestone produces the clean engine; the web layer milestone wraps it
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| EXEC-01 | core-capability | validated | M003/S01 | M003/S02 | 50 tests, screen_puts callable |
| EXEC-02 | core-capability | validated | M003/S01 | none | spread filter tests pass |
| EXEC-03 | core-capability | validated | M003/S01 | none | 12 math tests, D046 |
| EXEC-04 | core-capability | validated | M003/S01 | none | _PUT_DTE_MIN=14 ≥ 7 |
| EXEC-05 | core-capability | validated | M003/S02 | M003/S01 | 3 strategy integration tests |
| EXEC-06 | quality-attribute | validated | M003/S03 | M003/S02 | core/execution.py deleted |
| EXEC-07 | quality-attribute | validated | M003/S03 | M003/S02 | core/strategy.py deleted |
| EXEC-08 | quality-attribute | validated | M003/S04 | all | 425 passed, 0 failed |
| EXEC-09 | quality-attribute | validated | M003/S01 | M003/S02 | 53 tests in test_put_screener.py |
| EXEC-D01 | core-capability | deferred | none | none | unmapped |
| EXEC-D02 | core-capability | deferred | none | none | unmapped |
| EXEC-X01 | core-capability | out-of-scope | none | none | n/a |
| EXEC-X02 | core-capability | out-of-scope | none | none | n/a |

## Coverage Summary

- Active requirements: 0
- Validated: 9
- Deferred: 2
- Out of scope: 2
- Unmapped active requirements: 0
