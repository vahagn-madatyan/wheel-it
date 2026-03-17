---
estimated_steps: 3
estimated_files: 16
---

# T01: Bring S01 API code from branch to main and install dependencies

**Slice:** S01 — FastAPI wraps existing screener engine
**Milestone:** M004

## Description

All S01 implementation (FastAPI app, routers, schemas, services, tests) exists on the `gsd/M004/S01` branch but is missing from the current working branch. The `apps/api/` directory on the current branch has only `__pycache__` artifacts — no `.py` source files. This task checks out the complete source tree from the branch and installs API-specific Python dependencies so tests can run in T02.

The API code lives entirely under `apps/api/` and does not modify any CLI files. It imports from existing CLI modules (`screener/put_screener.py`, `screener/call_screener.py`, `core/state_manager.py`, `screener/config_loader.py`) but never modifies them.

## Steps

1. Run `git checkout gsd/M004/S01 -- apps/` to bring all API source files from the branch to the working tree. This will create/overwrite files under `apps/api/` without affecting any other directories.

2. Verify all expected source files exist:
   ```bash
   find apps/api -name '*.py' -not -path '*__pycache__*' | sort
   ```
   Expected 16 files:
   - `apps/api/__init__.py`
   - `apps/api/main.py`
   - `apps/api/schemas.py`
   - `apps/api/requirements.txt` (not .py but important)
   - `apps/api/services/__init__.py`
   - `apps/api/services/clients.py`
   - `apps/api/services/task_store.py`
   - `apps/api/routers/__init__.py`
   - `apps/api/routers/screen.py`
   - `apps/api/routers/positions.py`
   - `apps/api/tests/__init__.py`
   - `apps/api/tests/conftest.py`
   - `apps/api/tests/test_client_factory.py`
   - `apps/api/tests/test_positions_account.py`
   - `apps/api/tests/test_screen_endpoints.py`
   - `apps/api/tests/test_task_store.py`

3. Install API-specific dependencies:
   ```bash
   uv pip install -r apps/api/requirements.txt
   ```
   This installs: `fastapi>=0.110.0`, `uvicorn[standard]>=0.29.0`, `httpx>=0.27.0`, `pytest-asyncio>=0.23.0`, `pydantic>=2.0.0`. Some may already be installed (pydantic is used by the CLI).

4. Smoke-test the import:
   ```bash
   python -c "from apps.api.main import app; print(app.title)"
   ```
   Expected output: `Wheeely Screening API`

## Must-Haves

- [ ] All 16 `.py` files under `apps/api/` are present on the working branch
- [ ] `apps/api/requirements.txt` is present
- [ ] `uv pip install -r apps/api/requirements.txt` completes without errors
- [ ] `python -c "from apps.api.main import app; print(app.title)"` prints `Wheeely Screening API`

## Verification

- `find apps/api -name '*.py' -not -path '*__pycache__*' | wc -l` returns 16
- `python -c "from apps.api.main import app; print(app.title)"` prints `Wheeely Screening API`
- `cat apps/api/requirements.txt` shows 5 dependency lines

## Observability Impact

- **What changes:** The `apps/api/` directory gains 16 Python source files that weren't previously on the working branch. No runtime behavior changes since the API server isn't started — this is a file-checkout + dependency-install task.
- **How to inspect:** `find apps/api -name '*.py' -not -path '*__pycache__*' | wc -l` confirms file count; `uv pip list | grep -i fastapi` confirms dependency installation.
- **Failure visibility:** If checkout fails, `find` returns <16 files. If dependency install fails, the smoke-test import will raise `ModuleNotFoundError` for `fastapi` or `httpx`.

## Inputs

- `gsd/M004/S01` branch — contains the complete `apps/api/` source tree with all 16 Python files
- Working branch has `apps/api/` directory with only `__pycache__` artifacts (no `.py` files)
- Project virtual environment is at `.venv/` managed by `uv`

## Expected Output

- `apps/api/main.py` — FastAPI app with lifespan (TaskStore + periodic cleanup), CORS middleware, screen + positions routers
- `apps/api/schemas.py` — 14 Pydantic models for request/response validation
- `apps/api/services/clients.py` — `create_alpaca_clients()` factory: builds 3 SDK clients from provided keys
- `apps/api/services/task_store.py` — `TaskStore` class: submit/update/get/cleanup lifecycle for background tasks
- `apps/api/routers/screen.py` — PUT/CALL screening endpoints (submit 202, poll, background execution via `asyncio.to_thread`)
- `apps/api/routers/positions.py` — Positions and account endpoints with per-request client construction
- `apps/api/tests/` — 4 test files with 31+ tests covering all endpoints and services
- `apps/api/requirements.txt` — API-specific dependencies (separate from CLI)
