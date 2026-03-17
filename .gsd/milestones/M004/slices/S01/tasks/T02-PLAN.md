---
estimated_steps: 4
estimated_files: 4
---

# T02: Run full test suites and validate S01 contracts

**Slice:** S01 — FastAPI wraps existing screener engine
**Milestone:** M004

## Description

This task proves S01's two owned requirements by running both test suites and confirming every contract assertion passes. **CLI-COMPAT-01**: the 425 existing CLI tests must still pass — proving that adding `apps/api/` code didn't break any CLI import paths, behavior, or dependencies. **WEB-11**: the 31+ API tests must pass — proving that the submit→poll background task pattern works, all endpoints return correct status codes and typed results, and error paths are handled.

If any tests fail, this task diagnoses and fixes them. Likely failure causes (from research): missing dependency, import path issue from editable install, or test timing sensitivity in background task tests. Logic bugs are unlikely since these tests passed on the `gsd/M004/S01` branch.

## Steps

1. Run the CLI test suite:
   ```bash
   python -m pytest tests/ -q
   ```
   Expected: 425 passed (the exact count may vary slightly if tests were added since the research was written — the key is zero failures).

2. Run the API test suite:
   ```bash
   python -m pytest apps/api/tests/ -v
   ```
   Expected: 31+ passed across 4 test files:
   - `test_task_store.py` — 9 tests (submit, get, update, cleanup lifecycle)
   - `test_client_factory.py` — 3 tests (return types, paper vs live, no env vars)
   - `test_screen_endpoints.py` — 12 tests (submit 202, poll completed, 404, status progression, failure capture, invalid preset 400, pending observation, schema validation)
   - `test_positions_account.py` — 9 tests (wheel state, empty portfolio, API error 502, account summary, risk calculation, missing keys 422)

3. If any tests fail, diagnose the root cause:
   - **Import errors**: Check that `apps/api/__init__.py`, `apps/api/routers/__init__.py`, `apps/api/services/__init__.py`, `apps/api/tests/__init__.py` all exist (even if empty). Verify the project is installed in editable mode (`uv pip install -e .`).
   - **Missing dependency**: Run `uv pip install -r apps/api/requirements.txt` if `httpx`, `pytest-asyncio`, or `fastapi` are missing.
   - **Timing-sensitive failures**: The screening endpoint tests use `time.sleep(0.5)` to wait for background tasks. If a test fails with status still `pending` or `running`, increase the sleep to `1.0`.
   - **CLI test regression**: If a CLI test that previously passed now fails, check if any CLI file was inadvertently modified by the branch checkout. Run `git diff HEAD -- screener/ core/ config/ logging/ scripts/ tests/` to verify zero CLI changes.

4. Run the import smoke test as final confirmation:
   ```bash
   python -c "from apps.api.main import app; print(app.title)"
   ```

## Must-Haves

- [ ] `python -m pytest tests/ -q` passes with zero failures (CLI-COMPAT-01)
- [ ] `python -m pytest apps/api/tests/ -v` passes with zero failures (WEB-11)
- [ ] Key endpoint contracts verified: 202 submit, completed poll with typed results, 404 unknown run, 400 invalid preset, 422 missing keys, 502 API error

## Verification

- `python -m pytest tests/ -q` — output shows "N passed" with zero failures
- `python -m pytest apps/api/tests/ -v` — output shows "N passed" with zero failures
- Both commands return exit code 0

## Observability Impact

- Signals added/changed: No new runtime signals — this task only validates existing test coverage
- How a future agent inspects this: Run the same two pytest commands to re-verify
- Failure state exposed: Test failure output includes assertion details, traceback, and the specific contract that broke

## Inputs

- `apps/api/` — complete source tree from T01 (16 Python files + requirements.txt)
- `tests/` — existing CLI test suite (425 tests)
- API dependencies installed from T01

## Expected Output

- Both test suites pass with zero failures
- CLI-COMPAT-01 proven: 425 CLI tests pass, zero CLI files modified
- WEB-11 proven: submit→poll pattern works, all status codes correct, typed results returned
- Slice S01 is verified and ready for downstream consumption by S02, S05, S06
