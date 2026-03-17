# S01: FastAPI wraps existing screener engine — Research

**Date:** 2026-03-16

## Summary

S01 is **already implemented and passing**. The `apps/api/` directory on the `gsd/M004/S01` branch contains a fully functional FastAPI app with 5 endpoints, per-request Alpaca client construction, in-memory TaskStore with submit→poll background tasks, Pydantic schemas, and a 31-test API suite — all green. The 425 CLI tests also pass unchanged (CLI-COMPAT-01 confirmed). Decisions D059–D062 were recorded during implementation.

The core discovery was that `screen_puts()` and `screen_calls()` are Alpaca-only — they accept raw SDK clients as parameters, never touch Finnhub or env vars. This made per-request client construction trivial: a 15-line factory function (`create_alpaca_clients()`) creates the three SDK clients from request-provided keys. No `BrokerClient` wrapper, no env var loading, no module-level side effects.

**Two issues remain unresolved** that downstream slices will encounter: (1) the `logging/` shadow package prevents uvicorn from starting when the project root is on `sys.path` (it masks `logging.config` from stdlib), and (2) `asyncio.ensure_future()` is deprecated in Python 3.10+ (scheduled for removal in 3.14). Both are documented but not blocking for test-level verification — tests use FastAPI's TestClient which doesn't go through uvicorn.

## Recommendation

**This slice appears complete. Re-verification only.** Run the existing test suites to confirm everything still passes, then mark as verified. If any tests have regressed since the summary was written, fix the specific failures. Do not rewrite existing code.

The two known issues (`logging.config` shadow and `ensure_future`) are deferred concerns — the logging shadow is a project-wide structural issue (D001/D062) that affects deployment (S07), not S01's contracts. The `ensure_future` deprecation is cosmetic on Python 3.13 and could be addressed as a minor cleanup in any future slice.

## Implementation Landscape

### Key Files

**Already built on `gsd/M004/S01` branch:**

- `apps/api/main.py` — FastAPI app with lifespan context manager (creates TaskStore, starts periodic cleanup coro), CORS middleware (all origins for dev), includes screen + positions routers.
- `apps/api/schemas.py` — 14 Pydantic models: `AlpacaKeysMixin` for credential inheritance, `PutScreenRequest`/`CallScreenRequest` for submit, `PutResultSchema`/`CallResultSchema` mirroring dataclass fields, `RunSubmitResponse`/`RunStatusResponse` for poll, `PositionSchema`/`WheelStateEntry`/`PositionsResponse`/`AccountResponse` for positions/account.
- `apps/api/services/clients.py` — `create_alpaca_clients(api_key, secret_key, is_paper)` → `(TradingClient, OptionHistoricalDataClient, StockHistoricalDataClient)`. No env vars, no BrokerClient wrapper.
- `apps/api/services/task_store.py` — `TaskStore` with `submit(run_type) → run_id`, `update(run_id, status, results, error)`, `get(run_id) → TaskEntry`, `cleanup(max_age)`. `TaskStatus` enum: PENDING/RUNNING/COMPLETED/FAILED. `periodic_cleanup()` async coroutine for lifespan.
- `apps/api/routers/screen.py` — `POST /api/screen/puts` and `/calls` (202 response, `asyncio.ensure_future` launches background coroutine that calls `asyncio.to_thread(screen_puts, ...)`, captures results or errors in TaskStore). `GET /api/screen/runs/{run_id}` polls status with typed results.
- `apps/api/routers/positions.py` — `GET /api/positions` (constructs per-request TradingClient, fetches positions via `asyncio.to_thread`, runs `update_state()`, returns positions + wheel_state). `GET /api/account` (fetches account + positions, runs `calculate_risk()`, returns summary).

**Existing CLI code reused unchanged:**

- `screener/put_screener.py:screen_puts()` — Accepts `trade_client, option_client, symbols, buying_power, config, stock_client`. Returns `list[PutRecommendation]`.
- `screener/call_screener.py:screen_calls()` — Accepts `trade_client, option_client, symbol, cost_basis, config`. Returns `list[CallRecommendation]`.
- `core/state_manager.py:update_state()` — Accepts position list, returns `dict[str, dict]` mapping underlying → wheel state.
- `core/state_manager.py:calculate_risk()` — Accepts position list, returns dollar risk float.
- `screener/config_loader.py:load_preset()` — Resolves preset YAML from `config/presets/`.

**Test suite (already built on branch):**

- `apps/api/tests/conftest.py` — Shared fixtures: `ALPACA_KEYS`, `ALPACA_QUERY_PARAMS`, `SAMPLE_PUT`, `SAMPLE_CALL`, `app_client` (async httpx), `mock_alpaca_triple`.
- `apps/api/tests/test_screen_endpoints.py` — 12 tests: submit 202, poll completed, unknown 404, status progression, failure capture, invalid preset 400, pending observation, schema field validation.
- `apps/api/tests/test_positions_account.py` — 9 tests: wheel state, empty portfolio, API error 502, account summary, risk calculation, missing keys 422.
- `apps/api/tests/test_task_store.py` — 9 tests: submit/get/update/cleanup lifecycle.
- `apps/api/tests/test_client_factory.py` — 3 tests: return types, paper vs live, no env vars.

### Build Order

1. **Cherry-pick or merge the `gsd/M004/S01` branch code to `main`** — all source files exist only on that branch. The current `main` has only `__pycache__` artifacts.
2. **Run both test suites** — `python -m pytest tests/ -q` (425 CLI tests) and `python -m pytest apps/api/tests/ -v` (31 API tests) to confirm everything is green.
3. **If tests pass, slice is verified.** If any fail, fix the specific regressions.

### Verification Approach

```bash
# CLI tests unchanged
python -m pytest tests/ -q
# Expected: 425 passed

# API tests
python -m pytest apps/api/tests/ -v
# Expected: 31 passed (or similar count)

# Smoke test (from non-project-root to avoid logging shadow):
cd /tmp && python -c "from apps.api.main import app; print(app.title)"
```

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| HTTP framework | FastAPI 0.135.1 (installed) | Already in use; Pydantic integration, OpenAPI docs |
| ASGI server | uvicorn (installed but blocked by logging shadow at project root) | Standard FastAPI companion; tests bypass via TestClient |
| Request/response validation | Pydantic v2 (already in project + API) | `ScreenerConfig` reused directly; consistent validation |
| Alpaca client construction | `alpaca-py` SDK (installed 0.43.2+) | `TradingClient(api_key=, secret_key=, paper=)` — trivial construction |
| Sync-to-async bridge | `asyncio.to_thread` (stdlib) | Used by screen.py and positions.py routers |
| Unique run IDs | `uuid.uuid4` (stdlib) | Used by TaskStore; collision-free at this scale |
| Background task state | `apps/api/services/task_store.py` (already built) | In-memory dict with TTL cleanup; D060 |

## Constraints

- **CLI import paths untouched.** All API code lives under `apps/api/`, completely outside CLI's package structure. `pyproject.toml` `[project.scripts]` entries and `[tool.setuptools.packages.find]` are unchanged.
- **API dependencies separate (D059).** FastAPI, uvicorn, httpx, pytest-asyncio listed in `apps/api/requirements.txt`, not root `pyproject.toml`. CLI install doesn't pull web deps.
- **`logging/` shadow blocks uvicorn from project root (D062).** The project's `logging/__init__.py` re-exports stdlib logging but doesn't expose `logging.config` submodule. Uvicorn imports `logging.config` at startup → `ModuleNotFoundError`. Tests work because TestClient doesn't go through uvicorn. **Deployment (S07) must address this.**
- **Screeners are synchronous.** `screen_puts()`/`screen_calls()` make blocking HTTP calls via requests. Must run in a thread via `asyncio.to_thread()` — never directly on the event loop.
- **`apps/` not in editable install.** The `[tool.setuptools.packages.find]` config includes packages at project root but `apps/` is not in `top_level.txt`. Import works because the editable install path hook resolves `apps.api` from the project root. Non-editable deployment needs explicit PYTHONPATH or package inclusion.
- **Source files only exist on `gsd/M004/S01` branch.** Current `main` has only `__pycache__` — a merge or cherry-pick is needed before any execution.

## Common Pitfalls

- **`asyncio.ensure_future()` deprecated** — Used in `screen.py`. Deprecated since Python 3.10, still works on 3.13, but scheduled for removal in 3.14. Should be `asyncio.create_task()` instead. Non-blocking for current runtime but a ticking clock.
- **Credentials in query string for GET endpoints** — `GET /api/positions` and `GET /api/account` accept `alpaca_api_key` and `alpaca_secret_key` as query parameters. These end up in server access logs and browser history. Acceptable for S01 (no auth layer yet) — S02 replaces with JWT auth + encrypted key decryption.
- **Task store is in-memory** — Screening results lost on process restart. Acceptable per D060; S02+ adds persistence.
- **CORS wide open** — `allow_origins=["*"]`. Development convenience; S07 tightens for production.
- **No rate limiting** — Any client can submit unlimited screening runs. S06 adds Redis sliding window.
- **`load_preset()` depends on `_PROJECT_ROOT`** — Resolved from `screener/config_loader.py`'s `__file__`. Works with editable install. In Docker, must ensure correct project structure.

## Open Risks

- **Uvicorn startup blocked by logging shadow (D062)** — Tests pass, but actually running the server requires workarounds. This will surface hard in S07 (deployment). Potential fixes: (a) rename `logging/` to `wheeely_logging/` (breaks CLI — violates CLI-COMPAT-01), (b) add `logging.config` forwarding to `__init__.py`, (c) Docker entrypoint that avoids putting project root on path.
- **`apps/` package discovery in production** — Editable install's path hook handles imports now, but a production pip install won't include `apps/` unless `pyproject.toml` is updated or deployment uses a separate install mechanism. S07 concern.
- **Thread pool exhaustion under concurrent screening** — Default pool size is `min(32, cpu_count + 4)`. Each screening run occupies a thread for 30-60s. If 30+ users screen simultaneously, queue starvation. Mitigated by S06 rate limiting (3/day) and MVP user count.
- **`ensure_future` Python 3.14 breakage** — Low urgency since Python 3.14 is >1 year away, but worth fixing proactively.

## Requirements Mapping

### Owned by S01

| Requirement | Status | How Addressed |
|-------------|--------|---------------|
| WEB-11 (async screening via background tasks) | ✅ Implemented | Submit→poll pattern with TaskStore + asyncio.to_thread(); 12 endpoint tests |
| CLI-COMPAT-01 (CLI works unchanged) | ✅ Verified | 425 tests pass; zero files outside apps/api/ modified |

### Supported by S01 (owned by other slices)

| Requirement | Status | What S01 Provides |
|-------------|--------|-------------------|
| WEB-05 (put screener in browser) | Infrastructure ready | POST /api/screen/puts + GET /api/screen/runs/{id} |
| WEB-06 (call screener in browser) | Infrastructure ready | POST /api/screen/calls + GET /api/screen/runs/{id} |
| WEB-07 (positions with wheel state) | Infrastructure ready | GET /api/positions |
| WEB-08 (account summary) | Infrastructure ready | GET /api/account |

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| FastAPI | `wshobson/agents@fastapi-templates` (6.6K installs) | available — not needed (slice already implemented) |
| FastAPI | `mindrally/skills@fastapi-python` (2.2K installs) | available — not needed |

## Sources

- Codebase exploration: `apps/api/` fully implemented on `gsd/M004/S01` branch (31 tests all green)
- Runtime verification: `python -m pytest tests/ -q` → 425 passed on main branch
- `logging.config` shadow confirmed: `importlib.util.find_spec('logging.config')` returns None when project `logging/` is on path
- FastAPI lifespan pattern confirmed via Context7 `/fastapi/fastapi` docs
- Decisions register: D059–D062 document all architectural choices made during S01 implementation
