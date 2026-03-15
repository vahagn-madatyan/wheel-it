# S03: Legacy Code Removal + Docs Update

**Goal:** Remove all dead legacy code paths that `screen_puts()` and `screen_calls()` replaced, and update project documentation.
**Demo:** `core/strategy.py` is deleted, `core/execution.py` is deleted, `models/contract.py` is deleted, obsolete constants are removed from `config/params.py`, and all 368+ tests still pass with zero import errors.

## Must-Haves

- `core/strategy.py` deleted (all 4 functions replaced by screener modules)
- `core/execution.py` deleted (`sell_puts` replaced by S02, `sell_calls` dead since M001/S10)
- `models/contract.py` deleted (replaced by `PutRecommendation` and `CallRecommendation` dataclasses)
- `config/params.py` cleaned: remove `YIELD_MIN`, `YIELD_MAX`, `SCORE_MIN`, `OPEN_INTEREST_MIN`, `EXPIRATION_MIN`, `EXPIRATION_MAX` (only `MAX_RISK`, `DELTA_MIN`, `DELTA_MAX` remain)
- No remaining imports of deleted modules anywhere in codebase
- `CLAUDE.md` Architecture section updated: remove references to `core/strategy.py`, `core/execution.py`, `models/contract.py`; add `screener/put_screener.py` description
- All tests pass

## Verification

- `python -m pytest tests/ -q` — all tests pass
- `rg "from core.strategy" .` — zero matches
- `rg "from core.execution" .` — zero matches
- `rg "from models.contract" .` — zero matches
- `rg "YIELD_MIN|YIELD_MAX|SCORE_MIN|OPEN_INTEREST_MIN|EXPIRATION_MIN|EXPIRATION_MAX" . --glob '*.py'` — zero matches (except possibly tests that test removed code, which should also be removed)

## Tasks

- [x] **T01: Delete legacy modules and clean config/params.py** `est:30m`
  - Why: These modules are dead code — all functionality replaced by screener modules
  - Files: `core/strategy.py` (delete), `core/execution.py` (delete), `models/contract.py` (delete), `config/params.py` (edit)
  - Do: Delete `core/strategy.py`. Delete `core/execution.py`. Delete `models/contract.py`. Edit `config/params.py` to remove `YIELD_MIN`, `YIELD_MAX`, `SCORE_MIN`, `OPEN_INTEREST_MIN`, `EXPIRATION_MIN`, `EXPIRATION_MAX`. Keep only `MAX_RISK`, `DELTA_MIN`, `DELTA_MAX`. Search for any remaining imports of deleted modules (`rg "from core.strategy|from core.execution|from models.contract"`) and fix them. Remove `import numpy as np` from `core/execution.py` consumers if applicable. Fix `core/broker_client.py` if it imports from `config/params.py` for `EXPIRATION_MIN`/`EXPIRATION_MAX` — replace with local constants or pass as parameters. Remove any test files that exclusively test deleted modules.
  - Verify: `python -m pytest tests/ -q` — all tests pass; `rg "from core.strategy|from core.execution|from models.contract" .` — zero matches
  - Done when: All deleted modules are gone, no import errors, all tests pass

- [x] **T02: Update CLAUDE.md and README.md** `est:20m`
  - Why: Documentation must reflect the new architecture so future sessions don't reference deleted modules
  - Files: `CLAUDE.md`, `README.md`
  - Do: Update CLAUDE.md Architecture section: remove `core/strategy.py` and `core/execution.py` descriptions, add `screener/put_screener.py` description, update `models/contract.py` to note it's removed, update `config/params.py` description to list only remaining constants. Update README.md: add `run-put-screener` CLI usage example, update architecture description. Verify `CLAUDE.md` `Key Modules` section is accurate.
  - Verify: Read `CLAUDE.md` and confirm no references to deleted modules
  - Done when: Both docs accurately describe the current codebase

## Files Likely Touched

- `core/strategy.py` (delete)
- `core/execution.py` (delete)
- `models/contract.py` (delete)
- `config/params.py` (edit)
- `core/broker_client.py` (edit — remove EXPIRATION_MIN/MAX import)
- `CLAUDE.md` (edit)
- `README.md` (edit)
