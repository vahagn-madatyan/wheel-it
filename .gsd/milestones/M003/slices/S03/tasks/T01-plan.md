---
estimated_steps: 6
estimated_files: 7
---

# T01: Delete legacy modules and clean config/params.py

**Slice:** S03 — Legacy Code Removal + Docs Update
**Milestone:** M003

## Description

Remove all dead legacy code: `core/strategy.py`, `core/execution.py`, `models/contract.py`, and obsolete constants from `config/params.py`. Fix any broken imports that result.

## Steps

1. Run `rg "from core.strategy|from core.execution|from models.contract" . --glob '*.py' -l` to identify all files importing from legacy modules.
2. Delete `core/strategy.py`.
3. Delete `core/execution.py`.
4. Delete `models/contract.py`.
5. Edit `config/params.py`: remove `YIELD_MIN`, `YIELD_MAX`, `SCORE_MIN`, `OPEN_INTEREST_MIN`, `EXPIRATION_MIN`, `EXPIRATION_MAX`. Keep `MAX_RISK`, `DELTA_MIN`, `DELTA_MAX`.
6. Fix `core/broker_client.py`: it imports `EXPIRATION_MIN`, `EXPIRATION_MAX` from `config.params`. The `get_options_contracts()` method on `BrokerClient` uses these — this method is now dead code (call screener and put screener use `trade_client` directly). Remove the import and either delete `get_options_contracts()` or replace with local constants. Also check if any other methods are still used — `get_positions()`, `market_sell()`, `get_stock_latest_trade()`, `get_option_snapshot()`, `liquidate_all_positions()` are still used by `run_strategy.py`.
7. Search for any test files that import from deleted modules and fix them. Run `python -m pytest tests/ -q` to confirm all tests pass.

## Must-Haves

- [ ] `core/strategy.py` does not exist
- [ ] `core/execution.py` does not exist
- [ ] `models/contract.py` does not exist
- [ ] `config/params.py` contains only `MAX_RISK`, `DELTA_MIN`, `DELTA_MAX`
- [ ] `rg "from core.strategy|from core.execution|from models.contract" . --glob '*.py'` — zero matches
- [ ] `rg "YIELD_MIN|YIELD_MAX|SCORE_MIN|OPEN_INTEREST_MIN|EXPIRATION_MIN|EXPIRATION_MAX" . --glob '*.py'` — zero matches
- [ ] All tests pass

## Verification

- `python -m pytest tests/ -q` — all pass
- `rg "from core.strategy|from core.execution|from models.contract" . --glob '*.py'` — zero
- `rg "YIELD_MIN|YIELD_MAX|SCORE_MIN|OPEN_INTEREST_MIN" . --glob '*.py'` — zero

## Inputs

- S02 completed: `run_strategy.py` no longer imports from `core.execution`
- Knowledge of which `BrokerClient` methods are still used

## Expected Output

- Deleted: `core/strategy.py`, `core/execution.py`, `models/contract.py`
- Modified: `config/params.py`, `core/broker_client.py`
- Clean test suite with zero import errors
