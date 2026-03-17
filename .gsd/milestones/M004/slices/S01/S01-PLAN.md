# S01: FastAPI wraps existing screener engine

**Goal:** FastAPI endpoints wrap the existing `screen_puts()`, `screen_calls()`, `update_state()`, and `calculate_risk()` functions with per-request Alpaca client construction and async background task execution. CLI remains untouched.
**Demo:** `POST /api/screen/puts` with Alpaca keys and symbols returns 202 with a `run_id`. `GET /api/screen/runs/{run_id}` polls until status is `completed` with JSON put recommendations. `GET /api/positions` and `GET /api/account` return positions with wheel state and account summary. 425 CLI tests still pass.

## Must-Haves

- `POST /api/screen/puts` accepts `{symbols, buying_power, preset, alpaca_api_key, alpaca_secret_key, is_paper}`, returns 202 with `{run_id, status}`
- `POST /api/screen/calls` accepts `{symbol, cost_basis, preset, alpaca_api_key, alpaca_secret_key, is_paper}`, returns 202 with `{run_id, status}`
- `GET /api/screen/runs/{run_id}` returns `{status, run_type, results, error}` with typed put/call results
- `GET /api/positions` returns positions list with wheel state classification
- `GET /api/account` returns buying power, portfolio value, cash, capital at risk
- Per-request Alpaca client construction from provided keys (no env vars, no BrokerClient)
- Background task pattern: submit→poll via in-memory TaskStore with TTL cleanup
- Invalid preset returns 400; missing keys returns 422; Alpaca API errors return 502
- 425 CLI tests pass unchanged — zero files outside `apps/api/` modified
- 31+ API tests pass covering all endpoints, error paths, and schema validation

## Proof Level

- This slice proves: contract
- Real runtime required: no (TestClient mocks suffice; real Alpaca calls tested by downstream slices)
- Human/UAT required: no

## Verification

- `python -m pytest tests/ -q` — 425 CLI tests pass (CLI-COMPAT-01)
- `python -m pytest apps/api/tests/ -v` — 31+ API tests pass (WEB-11 + all endpoint contracts)
- `python -c "from apps.api.main import app; print(app.title)"` — import smoke test
- `python -m pytest apps/api/tests/ -v -k "invalid or error or 404 or 400 or 502"` — failure-path tests pass (unknown run_id → 404, invalid preset → 400, Alpaca API errors → 502)

## Observability / Diagnostics

- Runtime signals: `TaskStore` status transitions (PENDING → RUNNING → COMPLETED/FAILED), Python `logging` in screen.py and positions.py routers
- Inspection surfaces: `GET /api/screen/runs/{run_id}` exposes task status, results, and error messages
- Failure visibility: Failed screening runs expose error string via TaskStore; Alpaca API errors surface as 502 with detail message
- Redaction constraints: Alpaca API keys in request bodies/query params — acceptable for S01 (no auth layer); S02 replaces with JWT + encrypted key decryption

## Integration Closure

- Upstream surfaces consumed: `screener/put_screener.py:screen_puts()`, `screener/call_screener.py:screen_calls()`, `core/state_manager.py:update_state()` and `calculate_risk()`, `screener/config_loader.py:load_preset()` — all used unchanged
- New wiring introduced in this slice: `apps/api/main.py` FastAPI app with lifespan (TaskStore + cleanup), CORS middleware, two routers; `apps/api/services/clients.py` per-request Alpaca client factory
- What remains before the milestone is truly usable end-to-end: S02 (auth + DB + encryption), S03 (frontend shell), S04 (key management UI), S05 (screener UI), S06 (positions dashboard + rate limiting), S07 (deployment)

## Tasks

- [x] **T01: Bring S01 API code from branch to main and install dependencies** `est:20m`
  - Why: All S01 source code exists only on the `gsd/M004/S01` branch. Main has only `__pycache__` in `apps/`. Must checkout the 16 source files and install API-specific dependencies before tests can run.
  - Files: `apps/api/main.py`, `apps/api/schemas.py`, `apps/api/services/clients.py`, `apps/api/services/task_store.py`, `apps/api/routers/screen.py`, `apps/api/routers/positions.py`, `apps/api/requirements.txt`, `apps/api/tests/conftest.py`, `apps/api/tests/test_*.py`, `apps/api/__init__.py`, `apps/api/routers/__init__.py`, `apps/api/services/__init__.py`, `apps/api/tests/__init__.py`
  - Do: (1) `git checkout gsd/M004/S01 -- apps/` to bring all source files from the branch. (2) `uv pip install -r apps/api/requirements.txt` to install FastAPI, uvicorn, httpx, pytest-asyncio. (3) Verify all 16 files exist and `python -c "from apps.api.main import app; print(app.title)"` succeeds.
  - Verify: `find apps/api -name '*.py' -not -path '*__pycache__*' | wc -l` returns 16; import smoke test prints "Wheeely Screening API"
  - Done when: All 16 source files present on current branch, API deps installed, import succeeds without errors

- [ ] **T02: Run full test suites and validate S01 contracts** `est:20m`
  - Why: S01's contracts are only proven when both the 425 CLI tests (CLI-COMPAT-01) and 31+ API tests (WEB-11) pass. This is the slice's objective stopping condition.
  - Files: `apps/api/tests/test_screen_endpoints.py`, `apps/api/tests/test_positions_account.py`, `apps/api/tests/test_task_store.py`, `apps/api/tests/test_client_factory.py`, `tests/` (existing CLI tests)
  - Do: (1) Run `python -m pytest tests/ -q` and confirm 425 tests pass. (2) Run `python -m pytest apps/api/tests/ -v` and confirm 31+ tests pass. (3) If any tests fail, diagnose and fix — likely causes are missing deps or import path issues, not logic bugs. (4) Verify key contract assertions: submit returns 202, poll returns completed with typed results, unknown run_id returns 404, invalid preset returns 400, missing keys returns 422, API errors return 502.
  - Verify: `python -m pytest tests/ -q && python -m pytest apps/api/tests/ -v` — both suites green
  - Done when: 425 CLI tests pass, 31+ API tests pass, zero test failures

## Files Likely Touched

- `apps/api/__init__.py`
- `apps/api/main.py`
- `apps/api/schemas.py`
- `apps/api/requirements.txt`
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
