---
id: T01
parent: S05
milestone: M004
provides:
  - retrieve_alpaca_keys shared helper for auth-aware key retrieval
  - Auth-protected screen and positions endpoints (no raw keys in requests)
  - Updated test suites with mock auth + mock key retrieval pattern
key_files:
  - apps/api/services/key_retrieval.py
  - apps/api/routers/screen.py
  - apps/api/routers/positions.py
  - apps/api/schemas.py
  - apps/api/tests/test_screen_endpoints.py
  - apps/api/tests/test_positions_account.py
key_decisions:
  - Missing auth returns 401 (HTTPBearer auto-raises), not 403 as plan hypothesized
patterns_established:
  - retrieve_alpaca_keys(user_id, db) pattern for any endpoint needing Alpaca credentials from DB
  - mock_key_retrieval fixture pattern: patch at router import path, return tuple
observability_surfaces:
  - retrieve_alpaca_keys logs "keys_retrieved" with provider and user_id on success
  - HTTPException 400 with descriptive messages for missing/incomplete/undecryptable keys
duration: 12m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Switch screen + positions endpoints to auth + DB-stored keys

**Created retrieve_alpaca_keys() shared helper; all screen and positions endpoints now use JWT auth + DB-stored keys instead of raw keys in request bodies/query params**

## What Happened

Created `apps/api/services/key_retrieval.py` with `retrieve_alpaca_keys(user_id, db)` that queries `api_keys` table, decrypts via `decrypt_value()`, validates both keys are present, and returns `(api_key, secret_key, is_paper)`. This extracts the core pattern from `keys.py:verify_keys` into a reusable function.

Updated `screen.py`: all three endpoints (`POST /puts`, `POST /calls`, `GET /runs/{run_id}`) now require `Depends(get_current_user)`. The two submit endpoints also use `Depends(get_db)` + `retrieve_alpaca_keys()` to get keys instead of reading them from the request body.

Updated `positions.py`: both `GET /positions` and `GET /account` now use `Depends(get_current_user)` + `Depends(get_db)` + `retrieve_alpaca_keys()` instead of accepting keys as query parameters.

Updated `schemas.py`: removed `AlpacaKeysMixin`, `PositionsQuery`, and `AccountQuery`. `PutScreenRequest` and `CallScreenRequest` now inherit `BaseModel` directly with only screening params. `KeyStoreRequest` unchanged.

Rewrote all 19 existing tests across both test files to use `mock_auth`, `mock_db`, `mock_key_retrieval`, and `auth_headers` fixtures. Added 7 new tests for auth-required (401) and missing-keys (400) error paths. Total: 14 screen tests + 10 positions tests = 24 tests.

## Verification

- `python -m pytest apps/api/tests/ -v` — 67 passed (14 screen + 10 positions + 43 other)
- `python -m pytest tests/ -q` — 425 passed
- `grep -c "ALPACA_KEYS" apps/api/tests/test_screen_endpoints.py` → 0
- `grep -c "ALPACA_QUERY_PARAMS" apps/api/tests/test_positions_account.py` → 0
- `python -c "from apps.api.services.key_retrieval import retrieve_alpaca_keys; print('OK')"` → OK
- `grep -c "retrieve_alpaca_keys" apps/api/routers/screen.py apps/api/routers/positions.py` → 3, 3
- `grep -c "get_current_user" apps/api/routers/screen.py apps/api/routers/positions.py` → 4, 3

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -m pytest apps/api/tests/ -v` | 0 | ✅ pass | 8.8s |
| 2 | `python -m pytest tests/ -q` | 0 | ✅ pass | 1.0s |
| 3 | `grep -c "ALPACA_KEYS" apps/api/tests/test_screen_endpoints.py` | 0 (returns "0") | ✅ pass | <1s |
| 4 | `grep -c "ALPACA_QUERY_PARAMS" apps/api/tests/test_positions_account.py` | 0 (returns "0") | ✅ pass | <1s |
| 5 | `python -c "from apps.api.services.key_retrieval import retrieve_alpaca_keys; print('OK')"` | 0 | ✅ pass | <1s |
| 6 | `grep -c "retrieve_alpaca_keys" apps/api/routers/screen.py apps/api/routers/positions.py` | 0 | ✅ pass | <1s |
| 7 | `grep -c "get_current_user" apps/api/routers/screen.py apps/api/routers/positions.py` | 0 | ✅ pass | <1s |

### Slice-level verification (partial — T01 is not final task):

| # | Check | Status |
|---|-------|--------|
| 1 | API tests pass (≥19) | ✅ 67 passed |
| 2 | CLI 425 tests pass | ✅ 425 passed |
| 3 | `npm run build` zero errors | ⏳ pending T02/T03 |
| 4 | `retrieve_alpaca_keys` used in both routers | ✅ confirmed |
| 5 | `get_current_user` in both routers | ✅ confirmed |

## Diagnostics

- `retrieve_alpaca_keys` logs `keys_retrieved` with `provider=alpaca` and `user_id` on success
- Missing keys → HTTPException 400 "Alpaca API keys not configured. Add keys in Settings."
- Incomplete keys → HTTPException 400 "Alpaca requires both api_key and secret_key"
- Decrypt failure → HTTPException 400 "Failed to decrypt stored keys"
- Missing auth → 401 from HTTPBearer (no Authorization header) or JWT validation failure

## Deviations

- Plan expected 403 for missing auth; actual behavior is 401 (FastAPI's `HTTPBearer` raises 401 for missing credentials, unlike `HTTPBasic` which raises 403). Updated tests to expect 401.
- Plan expected ≥13 screen tests and ≥10 positions tests; delivered 14 screen and 10 positions tests.

## Known Issues

None.

## Files Created/Modified

- `apps/api/services/key_retrieval.py` — new shared helper: `retrieve_alpaca_keys(user_id, db) -> (api_key, secret_key, is_paper)`
- `apps/api/routers/screen.py` — all 3 endpoints now use `Depends(get_current_user)`, submit endpoints use `retrieve_alpaca_keys()`
- `apps/api/routers/positions.py` — both endpoints use `Depends(get_current_user)` + `retrieve_alpaca_keys()`, no query params
- `apps/api/schemas.py` — removed `AlpacaKeysMixin`, `PositionsQuery`, `AccountQuery`; screen requests inherit `BaseModel` directly
- `apps/api/tests/test_screen_endpoints.py` — 14 tests using mock auth + mock key retrieval (no `ALPACA_KEYS` in payloads)
- `apps/api/tests/test_positions_account.py` — 10 tests using mock auth + mock key retrieval (no `ALPACA_QUERY_PARAMS`)
