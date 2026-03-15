---
id: S03
milestone: M003
provides:
  - "Deleted core/strategy.py (4 legacy functions replaced by screener modules)"
  - "Deleted core/execution.py (sell_puts and sell_calls replaced)"
  - "Deleted models/contract.py (replaced by PutRecommendation and CallRecommendation)"
  - "Cleaned config/params.py — only MAX_RISK, DELTA_MIN, DELTA_MAX remain"
  - "Cleaned core/broker_client.py — removed dead methods and obsolete imports"
  - "Updated CLAUDE.md with accurate architecture, CLI commands, and module descriptions"
key_files:
  - config/params.py
  - core/broker_client.py
  - CLAUDE.md
key_decisions:
  - "D047/D048 executed: full legacy removal including BrokerClient.get_options_contracts()"
drill_down_paths:
  - .gsd/milestones/M003/slices/S03/tasks/T01-plan.md
  - .gsd/milestones/M003/slices/S03/tasks/T02-plan.md
duration: 15min
verification_result: pass
completed_at: 2026-03-15T10:40:00Z
---

# S03: Legacy Code Removal + Docs Update

**Deleted core/strategy.py, core/execution.py, models/contract.py, cleaned config/params.py and broker_client.py, updated CLAUDE.md — 425 tests still passing**

## What Happened

T01: Deleted 3 legacy modules (`core/strategy.py`, `core/execution.py`, `models/contract.py`). Cleaned `config/params.py` to keep only `MAX_RISK`, `DELTA_MIN`, `DELTA_MAX`. Cleaned `core/broker_client.py` — removed `get_options_contracts()`, `get_option_snapshot()`, `get_stock_latest_trade()` methods (all dead code since screeners use SDK clients directly), removed unused imports (`EXPIRATION_MIN`, `EXPIRATION_MAX`, `ContractType`, `AssetStatus`, `GetOptionContractsRequest`, etc.).

T02: Updated `CLAUDE.md` with accurate module descriptions, CLI commands including `run-put-screener`, test commands, and current architecture patterns.

## Files Deleted
- `core/strategy.py`
- `core/execution.py`
- `models/contract.py`

## Files Modified
- `config/params.py` — Stripped to 3 constants
- `core/broker_client.py` — Stripped to 3 methods + client initialization
- `CLAUDE.md` — Complete rewrite of Architecture section
