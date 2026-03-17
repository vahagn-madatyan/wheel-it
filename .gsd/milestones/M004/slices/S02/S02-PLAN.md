# S02: Supabase auth + database + encrypted key storage

**Goal:** Supabase project has `profiles`, `api_keys`, `screening_runs`, `screening_results` tables with RLS. FastAPI auth middleware verifies Supabase JWTs. API keys encrypt/decrypt round-trip via envelope encryption. Key management CRUD endpoints are operational.

**Demo:** `python -m pytest apps/api/tests/test_encryption.py apps/api/tests/test_auth.py apps/api/tests/test_keys_endpoints.py -v` passes. Encryption round-trip works. JWT verification rejects invalid/expired tokens. Key CRUD endpoints store encrypted keys and return status without leaking values. 425 CLI tests and 31 S01 API tests still pass.

## Must-Haves

- Envelope encryption service: `encrypt_value()` / `decrypt_value()` using AESGCM with per-key DEK wrapped by APP_ENCRYPTION_SECRET (D054)
- SQL migration file with all 4 tables (`profiles`, `api_keys`, `screening_runs`, `screening_results`), RLS policies using `auth.uid()`, and profile creation trigger
- JWT auth middleware: `get_current_user()` FastAPI dependency that verifies Supabase HS256 tokens, returns user_id UUID
- Async database connection pool via asyncpg
- Key management endpoints: `POST /api/keys/{provider}`, `GET /api/keys/status`, `DELETE /api/keys/{provider}`, `POST /api/keys/{provider}/verify`
- Key management Pydantic schemas for requests/responses
- All new code lives in `apps/api/` — no changes to CLI code
- All new deps go in `apps/api/requirements.txt` only — `pyproject.toml` untouched
- S01 endpoints remain unprotected (auth not retrofitted this slice)
- 425 CLI tests + 31 S01 API tests continue passing

## Proof Level

- This slice proves: contract — encryption round-trip, JWT verification, key CRUD with mocked DB
- Real runtime required: no (tests use mocked Supabase/DB; real Supabase integration is manual/deployment concern)
- Human/UAT required: no

## Verification

- `source .venv/bin/activate && python -m pytest apps/api/tests/test_encryption.py -v` — Encrypt/decrypt round-trip returns original. Wrong KEK raises InvalidTag. Different calls produce unique nonces. Empty and long strings work.
- `source .venv/bin/activate && python -m pytest apps/api/tests/test_auth.py -v` — Valid JWT returns user_id. Expired JWT returns 401. Missing header returns 403. Malformed token returns 401. Missing `sub` claim returns 401.
- `source .venv/bin/activate && python -m pytest apps/api/tests/test_keys_endpoints.py -v` — POST stores encrypted key (not plaintext). GET status returns provider names without values. DELETE removes key. POST verify returns success/failure status. Unauthenticated requests return 401/403.
- `source .venv/bin/activate && python -m pytest tests/ -q` — 425 CLI tests pass
- `source .venv/bin/activate && python -m pytest apps/api/tests/ -q` — All API tests pass (31 S01 + new S02 tests)

## Observability / Diagnostics

- Runtime signals: `logger.info("key_stored", provider=..., user_id=...)` / `logger.warning("auth_failed", reason=...)` structured log events on key ops and auth failures
- Inspection surfaces: `GET /api/keys/status` returns per-provider connection state without exposing key values; database `api_keys` table shows encrypted rows
- Failure visibility: JWT middleware returns 401 with `detail` describing failure reason (expired, invalid, missing sub); encryption errors surface as 500 with generic message (no key material in logs)
- Redaction constraints: Plaintext API keys must NEVER appear in logs, error messages, or API responses. Only encrypted bytea in DB. `GET /api/keys/status` returns boolean connected/not-connected, never key values.

## Integration Closure

- Upstream surfaces consumed: `apps/api/main.py` (FastAPI app — add new router), `apps/api/services/clients.py` (client factory — used by verify endpoint), `apps/api/schemas.py` (add key management models)
- New wiring introduced in this slice: `keys` router mounted in `main.py`; `get_current_user` dependency available for any endpoint to use; `database.py` connection pool initialized in app lifespan
- What remains before the milestone is truly usable end-to-end: S03 (frontend auth flow), S04 (key management UI), S05 (screener UI using stored keys), S06 (positions + rate limiting), S07 (deployment)

## Tasks

- [x] **T01: Build envelope encryption service with tests** `est:30m`
  - Why: Encryption is the highest-risk piece with zero external dependencies — proves D054 round-trip works in isolation before anything else
  - Files: `apps/api/services/encryption.py`, `apps/api/tests/test_encryption.py`, `apps/api/requirements.txt`
  - Do: Add `cryptography>=43.0.0` to requirements.txt. Implement `encrypt_value(plaintext: str)` returning `(encrypted_value, encrypted_dek, nonce, dek_nonce)` tuple and `decrypt_value(encrypted_value, encrypted_dek, nonce, dek_nonce)` returning plaintext string. Use AESGCM with 256-bit keys. KEK loaded from `APP_ENCRYPTION_SECRET` env var (base64-encoded 32 bytes). Generate fresh random DEK + nonces per call. Write comprehensive tests: round-trip, wrong KEK, nonce uniqueness across calls, empty string, long string, binary-safe values.
  - Verify: `source .venv/bin/activate && pip install cryptography>=43.0.0 && python -m pytest apps/api/tests/test_encryption.py -v`
  - Done when: All encryption tests pass; encrypt→decrypt returns original for all inputs; wrong KEK raises; nonces are unique

- [x] **T02: Write database schema migration and async connection pool** `est:30m`
  - Why: The SQL schema defines the contract all downstream slices consume (S03 needs profiles, S04 needs api_keys, S05/S06 need screening tables). The connection pool is needed by key management endpoints.
  - Files: `apps/api/migrations/001_initial_schema.sql`, `apps/api/services/database.py`, `apps/api/requirements.txt`
  - Do: Create `apps/api/migrations/` directory. Write `001_initial_schema.sql` with all 4 tables (profiles, api_keys, screening_runs, screening_results), RLS policies using `(select auth.uid())` subselect pattern, profile creation trigger (`handle_new_user` function). Add `asyncpg>=0.29.0` to requirements.txt. Implement `database.py` with `get_db_pool()` that creates/caches an asyncpg connection pool from `DATABASE_URL` env var, and `get_db()` async dependency that yields a connection from the pool. Schema must reference `auth.users` for foreign key on profiles and use `to authenticated` role in RLS policies.
  - Verify: `source .venv/bin/activate && pip install asyncpg>=0.29.0 && python -c "import asyncpg; print('asyncpg OK')"` and validate SQL syntax with a basic parse check
  - Done when: Migration SQL file exists with all 4 tables, RLS policies, and trigger. `database.py` exports `get_db_pool()` and `get_db()`. asyncpg is installed.

- [x] **T03: Build JWT auth middleware with Pydantic schemas and tests** `est:30m`
  - Why: JWT verification is the gateway for all authenticated endpoints. Key management schemas define the API contract for S04's frontend.
  - Files: `apps/api/services/auth.py`, `apps/api/tests/test_auth.py`, `apps/api/schemas.py`, `apps/api/requirements.txt`
  - Do: Add `python-jose[cryptography]>=3.3.0` to requirements.txt. Implement `get_current_user()` as a FastAPI dependency using `HTTPBearer` + `jose.jwt.decode()` with HS256 algorithm, `SUPABASE_JWT_SECRET` from env var, audience="authenticated". Returns user_id (UUID string from `sub` claim). Add Pydantic models to `schemas.py`: `KeyStoreRequest` (key_value: str, is_paper: Optional[bool]), `KeyStatusResponse` (provider: str, connected: bool, is_paper: Optional[bool]), `KeyVerifyResponse` (provider: str, valid: bool, error: Optional[str]). Write auth tests: valid token → user_id, expired token → 401, missing Authorization → 403, malformed token → 401, missing `sub` claim → 401. Tests must craft JWTs with `python-jose` using a test secret.
  - Verify: `source .venv/bin/activate && pip install "python-jose[cryptography]>=3.3.0" && python -m pytest apps/api/tests/test_auth.py -v`
  - Done when: Auth tests pass. `get_current_user` correctly validates/rejects JWTs. Key management Pydantic schemas exist in schemas.py.

- [x] **T04: Build key management endpoints, wire into main.py, verify full suite** `est:1h`
  - Why: This integrates encryption + auth + DB into the key CRUD endpoints that S04 consumes. Wiring into main.py makes the endpoints live. Final verification confirms nothing is broken.
  - Files: `apps/api/routers/keys.py`, `apps/api/tests/test_keys_endpoints.py`, `apps/api/main.py`, `apps/api/tests/conftest.py`
  - Do: Create `keys.py` router with prefix `/api/keys`. Implement 4 endpoints: (1) `POST /{provider}` — accepts `KeyStoreRequest`, encrypts key_value via encryption service, stores in DB (mocked in tests), provider must be "alpaca" or "finnhub", key_name derived from provider ("api_key"/"secret_key" for alpaca, "finnhub_key" for finnhub); (2) `GET /status` — returns list of `KeyStatusResponse` for all providers user has keys stored for; (3) `DELETE /{provider}` — removes all keys for provider+user; (4) `POST /{provider}/verify` — decrypts stored keys, makes lightweight API call (Alpaca `get_account()` or Finnhub company profile), returns `KeyVerifyResponse`. All endpoints use `Depends(get_current_user)` for auth. Wire `keys.router` into `main.py`. Add auth helper fixtures to `conftest.py` (mock `get_current_user` override). Write endpoint tests with mocked DB and encryption. Run full test suite: 425 CLI + all API tests pass.
  - Verify: `source .venv/bin/activate && python -m pytest apps/api/tests/test_keys_endpoints.py -v && python -m pytest apps/api/tests/ -q && python -m pytest tests/ -q`
  - Done when: Key endpoint tests pass. S01's 31 tests still pass. 425 CLI tests still pass. `POST /api/keys/alpaca` stores encrypted key. `GET /api/keys/status` returns provider list. `DELETE /api/keys/alpaca` removes keys. Unauthenticated requests get 401/403.

## Files Likely Touched

- `apps/api/services/encryption.py` (new)
- `apps/api/services/auth.py` (new)
- `apps/api/services/database.py` (new)
- `apps/api/routers/keys.py` (new)
- `apps/api/migrations/001_initial_schema.sql` (new)
- `apps/api/tests/test_encryption.py` (new)
- `apps/api/tests/test_auth.py` (new)
- `apps/api/tests/test_keys_endpoints.py` (new)
- `apps/api/tests/conftest.py` (modified — add auth fixtures)
- `apps/api/schemas.py` (modified — add key management models)
- `apps/api/main.py` (modified — add keys router)
- `apps/api/requirements.txt` (modified — add cryptography, python-jose, asyncpg)
