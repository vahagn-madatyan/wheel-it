---
id: T04
parent: S02
milestone: M004
provides:
  - "4 key management endpoints: POST /{provider}, GET /status, DELETE /{provider}, POST /{provider}/verify"
  - "Full S02 integration: encryption (T01) + database (T02) + auth (T03) wired into endpoint layer"
  - "conftest.py auth/db mock fixtures reusable by downstream S04-S06 tests"
key_files:
  - apps/api/routers/keys.py
  - apps/api/tests/test_keys_endpoints.py
  - apps/api/main.py
  - apps/api/tests/conftest.py
  - apps/api/schemas.py
key_decisions:
  - "Provider validation via explicit set check + 422, not Enum path parameter — allows clear error messages"
  - "key_name field added to KeyStoreRequest body (not separate path params per key type) — cleaner REST contract"
  - "Unauthenticated test accepts 401 OR 403 — HTTPBearer behavior varies by FastAPI version (>=0.109 returns 401)"
  - "Verify endpoint uses asyncio.to_thread for blocking SDK calls — keeps event loop responsive"
patterns_established:
  - "mock_auth fixture: app.dependency_overrides[get_current_user] = lambda: TEST_USER_ID"
  - "mock_db fixture: AsyncMock with async generator override for get_db dependency"
  - "mock_encryption fixture: monkeypatch.setenv for APP_ENCRYPTION_SECRET"
  - "Verify tests use real encrypt_value to create ciphertext, then mock asyncio.to_thread for SDK calls"
observability_surfaces:
  - "logger.info('key_stored', provider=..., key_name=..., user_id=...) on successful store"
  - "logger.info('key_deleted', provider=..., user_id=...) on delete"
  - "logger.info('key_verified', provider=..., valid=True/False) on verify"
  - "logger.warning('key_verify_decrypt_failed', ...) when decryption fails at verify time"
  - "GET /api/keys/status — runtime key state per user without exposing values"
duration: 15m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T04: Build key management endpoints, wire into main.py, verify full suite

**Integrated encryption + auth + DB into 4 CRUD endpoints for API key management with 14 passing tests and zero regressions.**

## What Happened

Created `apps/api/routers/keys.py` with 4 endpoints:
- `POST /api/keys/{provider}` — encrypts key_value via envelope encryption, upserts into api_keys table
- `GET /api/keys/status` — returns provider list with connected status, never exposes key values
- `DELETE /api/keys/{provider}` — removes all keys for a provider
- `POST /api/keys/{provider}/verify` — decrypts stored keys, tests connectivity via Alpaca `get_account()` or Finnhub `market_status()`

Added `key_name: str` field to `KeyStoreRequest` in schemas.py — allows alpaca to store `api_key` and `secret_key` separately while finnhub stores just `api_key`.

Wired `keys.router` into `main.py` alongside existing screen and positions routers. S01 endpoints remain unprotected.

Updated `conftest.py` with `mock_auth`, `mock_db`, `mock_encryption`, and `auth_headers` fixtures for S02+ tests.

## Verification

- `python -m pytest apps/api/tests/test_keys_endpoints.py -v` — **14 passed** (store alpaca/finnhub, invalid provider/key_name, status full/empty, delete valid/invalid, verify success/failure/no-keys/invalid-provider, unauthenticated rejection)
- `python -m pytest apps/api/tests/ -q` — **62 passed** (48 S01 + 14 S02)
- `python -m pytest tests/ -q` — **425 passed** (CLI tests)
- Slice-level: `python -m pytest apps/api/tests/test_encryption.py apps/api/tests/test_auth.py apps/api/tests/test_keys_endpoints.py -v` — **31 passed** (11 encryption + 6 auth + 14 keys)
- Plaintext leakage check: `test_store_alpaca_key` asserts mock DB received `bytes` for encrypted_value/encrypted_dek/nonce/dek_nonce and that `b"AKTEST123"` is not in encrypted_value

## Diagnostics

- **Key operations:** `logger.info("key_stored", ...)` / `logger.info("key_deleted", ...)` / `logger.info("key_verified", ...)` structured log events
- **Auth failures:** Propagated from auth.py as `logger.warning("auth_failed", reason=...)`
- **Verify failures:** Returns `valid=False` with sanitized error message (no stack traces)
- **Decrypt failures at verify:** `logger.warning("key_verify_decrypt_failed", ...)` — indicates KEK rotation or data corruption
- **Runtime inspection:** `GET /api/keys/status` returns per-provider connection state without key values

## Deviations

- Plan expected unauthenticated requests to return 403. Actual FastAPI >=0.109 HTTPBearer returns 401 for missing auth header. Test updated to accept either 401 or 403 (consistent with T03 findings).
- Plan suggested `"finnhub_key"` as a key_name option. Used `"api_key"` for finnhub instead to keep naming consistent across providers — both alpaca and finnhub use `"api_key"`.

## Known Issues

None.

## Files Created/Modified

- `apps/api/routers/keys.py` — New: 4 key management endpoints with auth + encryption + DB integration
- `apps/api/tests/test_keys_endpoints.py` — New: 14 endpoint tests with mocked DB/auth/encryption
- `apps/api/main.py` — Modified: added `keys.router` import and include_router call
- `apps/api/tests/conftest.py` — Modified: added mock_auth, mock_db, mock_encryption, auth_headers fixtures and S02 constants
- `apps/api/schemas.py` — Modified: added `key_name` field to `KeyStoreRequest`
