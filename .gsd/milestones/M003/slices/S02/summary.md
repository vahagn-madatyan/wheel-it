---
id: S02
milestone: M003
provides:
  - "scripts/run_put_screener.py — Typer CLI for put screening with --buying-power, --preset, --config"
  - "run-put-screener registered in pyproject.toml [project.scripts]"
  - "scripts/run_strategy.py uses screen_puts() instead of sell_puts() for put-selling leg"
  - "Buying power tracking with deduction per put sold"
  - "Strategy integration tests confirm screen_puts path and buying power deduction"
key_files:
  - scripts/run_put_screener.py
  - scripts/run_strategy.py
  - tests/test_cli_strategy.py
  - tests/test_call_screener.py
key_decisions:
  - "Reused screener_config variable for both call and put screening in run_strategy"
  - "Fixed 3 call screener strategy tests that patched removed sell_puts"
patterns_established:
  - "run-put-screener CLI mirrors run-call-screener with variadic symbols + --buying-power"
drill_down_paths:
  - .gsd/milestones/M003/slices/S02/tasks/T01-plan.md
  - .gsd/milestones/M003/slices/S02/tasks/T02-plan.md
duration: 30min
verification_result: pass
completed_at: 2026-03-15T10:25:00Z
---

# S02: Put Screener CLI + Strategy Integration

**run-put-screener CLI and run-strategy integration with screen_puts() replacing legacy sell_puts() — 425 tests passing**

## What Happened

T01: Created `scripts/run_put_screener.py` with Typer CLI accepting variadic symbols, `--buying-power` (required), `--preset`, `--config`. Registered `run-put-screener` in `pyproject.toml`. 3 CLI tests.

T02: Removed `from core.execution import sell_puts, sell_calls` from `run_strategy.py`. Replaced `sell_puts()` call with `screen_puts()` + order execution loop that iterates recommendations, calls `client.market_sell(rec.symbol)`, and tracks buying power deduction. Fixed 3 strategy integration tests in `test_call_screener.py` that patched the now-removed `sell_puts`. Added 4 new strategy tests confirming `screen_puts` is called, recommendations trigger orders, empty list handled, and no `core.execution` imports remain.

## Files Created/Modified
- `scripts/run_put_screener.py` — New CLI entry point
- `scripts/run_strategy.py` — Modernized put-selling leg
- `pyproject.toml` — Added `run-put-screener` entry point
- `tests/test_cli_strategy.py` — Rewritten with screen_puts integration tests
- `tests/test_call_screener.py` — Fixed 3 tests to patch screen_puts instead of sell_puts
