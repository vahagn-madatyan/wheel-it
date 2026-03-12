---
id: S10
parent: M001
milestone: M001
provides:
  - screener/call_screener.py — screen_calls() + render_call_results_table() + CallRecommendation dataclass
  - scripts/run_call_screener.py — Typer CLI entry point registered as run-call-screener
  - run-strategy integration — long_shares state triggers call screener instead of old sell_calls path
requires:
  - slice: S09
    provides: Options chain API integration patterns (OI/spread filtering), preset YAML thresholds, BrokerClient for Alpaca options API
affects: []
key_files:
  - screener/call_screener.py
  - scripts/run_call_screener.py
  - scripts/run_strategy.py
  - tests/test_call_screener.py
  - pyproject.toml
key_decisions:
  - D037: Call screener reuses put screener DTE range (14-60 days) and preset OI/spread thresholds; delta range from config/params.py
  - D038: Strategy integration replaces old sell_calls execution path with screen_calls for smarter covered call selection
  - D039: Contracts with no greeks data pass delta filter (same None-tolerance as Finnhub filters)
patterns_established:
  - CallRecommendation dataclass for structured call screening results
  - screen_calls() as a pure screening function (fetch → filter → rank) matching pipeline pattern
  - render_call_results_table() with Console injection for testability (D015 pattern reuse)
observability_surfaces:
  - render_call_results_table() shows "No covered call recommendations" when no contracts pass
  - run-strategy logs selected call contract details (symbol, strike, DTE, premium, ann.return)
  - run-strategy logs "No viable covered call found" when screening produces zero results
  - run-strategy logs error for insufficient shares (<100) without crashing
drill_down_paths:
  - tests/test_call_screener.py
duration: single session
verification_result: passed
completed_at: 2026-03-11
---

# S10: Covered Call Screening + Strategy Integration

**Standalone call screener CLI and strategy-integrated covered call selection for the wheel's second leg**

## What Happened

Built the complete covered call screening module (`screener/call_screener.py`) with three components: `screen_calls()` fetches OTM call contracts from Alpaca, filters by strike ≥ cost basis, OI minimum, bid/ask spread maximum, and delta range, then ranks survivors by annualized return. `render_call_results_table()` displays results as a Rich table with all required columns. `CallRecommendation` dataclass holds structured results.

Registered `run-call-screener` CLI entry point in `pyproject.toml` via `scripts/run_call_screener.py`, accepting symbol + `--cost-basis` arguments with optional `--preset` override. The CLI reuses the same config infrastructure (presets, YAML merge, Pydantic validation) as the put screener.

Integrated call screener into `scripts/run_strategy.py`: when `update_state()` reports `long_shares`, the strategy now uses `screen_calls()` to find the best covered call instead of the old `core/execution.py:sell_calls()` path. This gives the strategy access to preset-configurable OI/spread/delta thresholds and proper annualized return ranking. Added guard for insufficient shares (<100) that logs an error and skips instead of raising.

Wrote 43 tests covering: annualized return math (8 tests), dataclass structure (2 tests), core screening logic with all filter paths (17 tests), DTE range constants (1 test), Rich table output (4 tests), CLI entry point (3 tests), strategy integration (3 tests), preset threshold application (5 tests).

## Verification

- 43 new tests in `test_call_screener.py` — all pass
- 302 existing tests — all pass (zero regressions)
- Total: 345 tests, 0 failures
- `uv pip install -e .` installs cleanly with `run-call-screener` entry point

## Requirements Advanced

- None remaining in Active for S10 scope — all moved to Validated

## Requirements Validated

- CALL-01 — 3 CLI tests prove `run-call-screener` works as standalone CLI
- CALL-02 — `screen_calls()` accepts symbol + cost basis, returns ranked recommendations
- CALL-03 — `test_strike_below_cost_basis_excluded` + `test_strike_equal_to_cost_basis_included` prove enforcement
- CALL-04 — 6 filter tests prove OI/spread/delta filters applied; DTE range matches put screener (14-60)
- CALL-05 — `test_table_renders_with_data` verifies all 8 columns in Rich table output
- CALL-06 — 3 strategy integration tests prove `screen_calls` invoked for `long_shares` state

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- Strategy integration replaced the old `sell_calls()` execution path entirely rather than calling it as a fallback. The new `screen_calls()` is strictly better — same filtering plus preset-configurable thresholds and annualized return ranking.
- Added insufficient-shares guard (< 100) in `run_strategy.py` that logs and skips instead of raising `ValueError` as the old `sell_calls` did. Strategy should continue processing other symbols, not crash.

## Known Limitations

- Call screener uses hardcoded delta range from `config/params.py` (DELTA_MIN=0.15, DELTA_MAX=0.30) rather than preset-configurable delta thresholds. All three presets share the same delta bounds.
- No call-specific preset sections (e.g. `calls.delta_min`). The screener reuses the `options` section from put screening presets.
- `run-strategy` integration does not display the Rich table — it logs the selected call and places the order silently. Rich table display is only in the standalone CLI.

## Follow-ups

- none

## Files Created/Modified

- `screener/call_screener.py` — New module: `screen_calls()`, `compute_call_annualized_return()`, `render_call_results_table()`, `CallRecommendation` dataclass
- `scripts/run_call_screener.py` — New Typer CLI entry point for standalone call screening
- `scripts/run_strategy.py` — Integrated `screen_calls` for `long_shares` state, replacing old `sell_calls` path
- `pyproject.toml` — Added `run-call-screener` console script entry point
- `tests/test_call_screener.py` — 43 tests covering all call screener functionality
- `.gsd/REQUIREMENTS.md` — Moved CALL-01..06 from Active to Validated with proof references

## Forward Intelligence

### What the next slice should know
- This is the terminal slice in M001. All 25 requirements are now validated. The milestone is complete.

### What's fragile
- Delta range is hardcoded in `config/params.py` — if users want different delta bounds for calls vs puts, this will need to be split into separate config sections.

### Authoritative diagnostics
- `python -m pytest tests/test_call_screener.py -v` — 43 tests covering all call screening code paths
- `python -m pytest tests/ -q` — 345 total tests, full regression suite

### What assumptions changed
- Original `sell_calls` in `execution.py` used the old scoring formula from `core/strategy.py`. The new `screen_calls` replaces this with annualized return ranking and preset-configurable OI/spread thresholds — a strictly better approach.
