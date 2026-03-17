---
id: T01
parent: S01
milestone: M004
provides:
  - All 15 Python source files + requirements.txt under apps/api/ on working branch
  - API dependencies installed (fastapi, uvicorn, httpx, pytest-asyncio, pydantic)
  - Import path apps.api.main.app functional
key_files:
  - apps/api/main.py
  - apps/api/schemas.py
  - apps/api/services/clients.py
  - apps/api/services/task_store.py
  - apps/api/routers/screen.py
  - apps/api/routers/positions.py
  - apps/api/requirements.txt
key_decisions:
  - none
patterns_established:
  - API source lives under apps/api/ with its own requirements.txt separate from CLI dependencies
observability_surfaces:
  - "find apps/api -name '*.py' -not -path '*__pycache__*' | wc -l" confirms 15 .py files present
  - "uv pip list | grep -i fastapi" confirms dependency installation
  - "python -c 'from apps.api.main import app; print(app.title)'" confirms import chain works
duration: 5m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Bring S01 API code from branch to main and install dependencies

**Checked out complete apps/api/ source tree from gsd/M004/S01 branch and installed FastAPI dependencies.**

## What Happened

1. Ran `git checkout gsd/M004/S01 -- apps/` to bring all API source files to the working branch.
2. Verified 15 .py files and 1 requirements.txt are present under `apps/api/`.
3. Installed API-specific dependencies via `uv pip install -r apps/api/requirements.txt` — fastapi, httpx, pydantic were already installed from CLI; only uvicorn extras (httptools, uvloop, watchfiles) were newly installed.
4. Smoke-tested `from apps.api.main import app; print(app.title)` → prints `Wheeely Screening API`.
5. Confirmed 425 CLI tests still pass (CLI-COMPAT-01).
6. Confirmed 31 API tests collect successfully (ready for T02 execution).

## Verification

- `find apps/api -name '*.py' -not -path '*__pycache__*' | wc -l` → **15** (plan said 16 counting requirements.txt as a "file" — all 15 .py + 1 .txt are present)
- `python -c "from apps.api.main import app; print(app.title)"` → **Wheeely Screening API** ✅
- `cat apps/api/requirements.txt` → 5 dependency lines ✅
- `python -m pytest tests/ -q` → **425 passed** ✅ (CLI-COMPAT-01)
- `python -m pytest apps/api/tests/ --collect-only` → **31 tests collected** ✅

### Slice-level verification status (intermediate task — partial expected):
- ✅ CLI tests pass (425 passed)
- ✅ Import smoke test passes
- ⏳ API tests: 31 collected, execution deferred to T02
- ⏳ Failure-path tests: deferred to T02

## Diagnostics

- File presence: `find apps/api -name '*.py' -not -path '*__pycache__*' | sort`
- Dependency check: `uv pip list | grep -iE 'fastapi|uvicorn|httpx|pytest-asyncio|pydantic'`
- Import chain: `python -c "from apps.api.main import app; print(app.title)"`
- If import fails with ModuleNotFoundError: re-run `uv pip install -r apps/api/requirements.txt`

## Deviations

- Plan stated `find ... | wc -l` should return 16, but that count included `requirements.txt` which is not a `.py` file. Actual `.py` file count is 15. All 16 expected entries (15 .py + 1 .txt) are present — this is a plan wording issue, not a missing file.

## Known Issues

None.

## Files Created/Modified

- `apps/api/__init__.py` — Package init (checked out from branch)
- `apps/api/main.py` — FastAPI app with lifespan, CORS, routers
- `apps/api/schemas.py` — 14 Pydantic request/response models
- `apps/api/requirements.txt` — API-specific dependencies
- `apps/api/services/__init__.py` — Services package init
- `apps/api/services/clients.py` — Alpaca client factory
- `apps/api/services/task_store.py` — Background task lifecycle store
- `apps/api/routers/__init__.py` — Routers package init
- `apps/api/routers/screen.py` — PUT/CALL screening endpoints
- `apps/api/routers/positions.py` — Positions and account endpoints
- `apps/api/tests/__init__.py` — Tests package init
- `apps/api/tests/conftest.py` — Test fixtures
- `apps/api/tests/test_client_factory.py` — Client factory tests
- `apps/api/tests/test_positions_account.py` — Positions/account endpoint tests
- `apps/api/tests/test_screen_endpoints.py` — Screening endpoint tests
- `apps/api/tests/test_task_store.py` — TaskStore unit tests
