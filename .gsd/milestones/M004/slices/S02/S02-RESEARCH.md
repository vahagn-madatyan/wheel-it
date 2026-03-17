# S02: Supabase auth + database + encrypted key storage — Research

**Date:** 2026-03-16

## Summary

S02 introduces three major subsystems into the FastAPI backend: Supabase JWT authentication, database schema with Row Level Security, and envelope encryption for API key storage. The existing API from S01 currently accepts Alpaca credentials in request bodies — S02 must (1) add auth middleware that verifies Supabase JWTs on every request, (2) create Postgres tables (`profiles`, `api_keys`, `screening_runs`, `screening_results`) with RLS policies enforcing per-user isolation, (3) implement envelope encryption so API keys are encrypted at rest with a per-key DEK wrapped by APP_ENCRYPTION_SECRET, and (4) expose CRUD endpoints for key management.

The primary risk is that S02 produces the foundational security layer consumed by all downstream slices (S03 for frontend auth, S04 for key management UI, S05/S06 for screening with stored keys). If the JWT middleware, encryption round-trip, or RLS policies are wrong, everything downstream breaks. The work divides cleanly into three independent units (schema/RLS, JWT middleware, encryption service) plus an integration layer (key management endpoints).

No Supabase, JWT, or encryption libraries exist in the project today. The `cryptography` library (AESGCM) and `python-jose` (JWT decode via JWKS) are the right choices per D054 and Supabase's own docs. The Supabase Python client (`supabase-py`) is **not** needed server-side — FastAPI talks to Postgres directly, and JWT verification uses `python-jose` against the JWKS endpoint.

## Recommendation

Build in this order: (1) encryption service first — it's the riskiest piece and has zero external dependencies to set up; (2) database schema + RLS as SQL migration files — these define the contract downstream slices rely on; (3) JWT auth middleware — depends on SUPABASE_URL/SUPABASE_JWT_SECRET env vars but is mechanically straightforward; (4) key management endpoints — integrates the previous three. Each unit is independently testable.

Use application-level envelope encryption with `cryptography.hazmat.primitives.ciphers.aead.AESGCM` (per D054), not Supabase Vault. Use `python-jose` for JWT verification against Supabase JWKS (Supabase's recommended Python approach). Store the schema as `.sql` migration files in `apps/api/migrations/` for reproducibility.

Do NOT refactor the S01 screen/positions routers to use stored keys in this slice. S02 produces the building blocks (auth middleware, encryption utils, key CRUD endpoints, database tables). S04 wires the frontend, and the router refactoring happens as part of S05/S06 when screening endpoints switch from request-body keys to decrypted-from-database keys.

## Implementation Landscape

### Key Files

**Existing (from S01, read-only context):**
- `apps/api/main.py` — FastAPI app; S02 adds auth middleware and new router here
- `apps/api/services/clients.py` — `create_alpaca_clients(api_key, secret_key, is_paper)` factory; S02's decryption utility must produce values compatible with this interface
- `apps/api/schemas.py` — Pydantic models; S02 adds key management schemas here
- `apps/api/routers/screen.py` — Currently takes keys in request body; will be refactored later (S05)
- `apps/api/routers/positions.py` — Same — keys in query params today
- `screener/finnhub_client.py` — `FinnhubClient(api_key=...)` already accepts optional key parameter (line 70–71)
- `config/credentials.py` — CLI credential loading; untouched by S02

**New files S02 creates:**
- `apps/api/services/encryption.py` — Envelope encryption: `encrypt_key()`, `decrypt_key()` using AESGCM with per-key DEK wrapped by APP_ENCRYPTION_SECRET
- `apps/api/services/auth.py` — `get_current_user()` FastAPI dependency that extracts + verifies Supabase JWT from `Authorization: Bearer <token>` header, returns user_id (UUID)
- `apps/api/services/database.py` — Async Postgres connection pool (asyncpg or psycopg[async]) configured from `DATABASE_URL` env var (Supabase connection string)
- `apps/api/routers/keys.py` — Key management endpoints: `POST /api/keys/{provider}`, `GET /api/keys/status`, `DELETE /api/keys/{provider}`, `POST /api/keys/{provider}/verify`
- `apps/api/migrations/001_initial_schema.sql` — Profiles, api_keys, screening_runs, screening_results tables + RLS policies + profile creation trigger
- `apps/api/tests/test_encryption.py` — Encrypt/decrypt round-trip, wrong-KEK detection, nonce uniqueness
- `apps/api/tests/test_auth.py` — JWT decode happy path, expired token, missing header, malformed token
- `apps/api/tests/test_keys_endpoints.py` — Key CRUD endpoint tests with mocked DB + encryption

### Database Schema

```sql
-- profiles: auto-populated on Supabase Auth signup
create table profiles (
  id uuid references auth.users not null primary key,
  email text,
  tier text default 'free' not null,
  created_at timestamptz default now() not null,
  updated_at timestamptz default now() not null
);

-- api_keys: envelope-encrypted credentials per user per provider
create table api_keys (
  id bigint generated always as identity primary key,
  user_id uuid references profiles(id) on delete cascade not null,
  provider text not null,          -- 'alpaca' or 'finnhub'
  key_name text not null,          -- 'api_key', 'secret_key', 'finnhub_key'
  encrypted_value bytea not null,  -- AES-GCM ciphertext (DEK-encrypted)
  encrypted_dek bytea not null,    -- DEK wrapped by APP_ENCRYPTION_SECRET
  nonce bytea not null,            -- 12-byte AES-GCM nonce
  dek_nonce bytea not null,        -- 12-byte nonce for DEK wrapping
  is_paper boolean default true,   -- only meaningful for alpaca provider
  created_at timestamptz default now() not null,
  updated_at timestamptz default now() not null,
  unique(user_id, provider, key_name)
);

-- screening_runs: tracks async screening tasks
create table screening_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade not null,
  run_type text not null,          -- 'put_screen' or 'call_screen'
  status text not null default 'pending',
  params jsonb,                    -- input params (symbols, preset, etc.)
  error text,
  created_at timestamptz default now() not null,
  completed_at timestamptz
);

-- screening_results: results for completed runs
create table screening_results (
  id bigint generated always as identity primary key,
  run_id uuid references screening_runs(id) on delete cascade not null,
  data jsonb not null              -- serialized recommendation list
);
```

RLS policies follow the Supabase `auth.uid()` pattern (from the installed skill):
```sql
alter table profiles enable row level security;
alter table api_keys enable row level security;
alter table screening_runs enable row level security;
alter table screening_results enable row level security;

-- profiles: users see only their own
create policy "Users read own profile" on profiles for select to authenticated using (id = (select auth.uid()));
create policy "Users update own profile" on profiles for update to authenticated using (id = (select auth.uid()));

-- api_keys: full CRUD scoped to owner
create policy "Users manage own keys" on api_keys for all to authenticated using (user_id = (select auth.uid()));

-- screening_runs: users see only their own runs
create policy "Users manage own runs" on screening_runs for all to authenticated using (user_id = (select auth.uid()));

-- screening_results: users see results for their own runs
create policy "Users read own results" on screening_results for select to authenticated
  using (run_id in (select id from screening_runs where user_id = (select auth.uid())));
```

Profile creation trigger (fired by Supabase Auth on signup):
```sql
create or replace function public.handle_new_user()
returns trigger
set search_path = ''
as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email);
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
```

### Envelope Encryption Design

Per D054, use two-layer encryption:
1. **KEK (Key Encryption Key)** = `APP_ENCRYPTION_SECRET` env var, 32 bytes, base64-encoded
2. **DEK (Data Encryption Key)** = random 32-byte key generated per API key storage operation
3. **Encrypt flow:** generate DEK → encrypt plaintext key with DEK+nonce via AESGCM → encrypt DEK with KEK+dek_nonce via AESGCM → store (encrypted_value, encrypted_dek, nonce, dek_nonce)
4. **Decrypt flow:** decrypt DEK using KEK+dek_nonce → decrypt value using DEK+nonce → return plaintext

```python
# Pseudocode for apps/api/services/encryption.py
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os, base64

def _get_kek() -> bytes:
    raw = os.environ["APP_ENCRYPTION_SECRET"]
    return base64.b64decode(raw)  # 32 bytes

def encrypt_value(plaintext: str) -> tuple[bytes, bytes, bytes, bytes]:
    kek = _get_kek()
    dek = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)
    dek_nonce = os.urandom(12)
    encrypted_value = AESGCM(dek).encrypt(nonce, plaintext.encode(), None)
    encrypted_dek = AESGCM(kek).encrypt(dek_nonce, dek, None)
    return encrypted_value, encrypted_dek, nonce, dek_nonce

def decrypt_value(encrypted_value: bytes, encrypted_dek: bytes, nonce: bytes, dek_nonce: bytes) -> str:
    kek = _get_kek()
    dek = AESGCM(kek).decrypt(dek_nonce, encrypted_dek, None)
    plaintext = AESGCM(dek).decrypt(nonce, encrypted_value, None)
    return plaintext.decode()
```

### JWT Auth Middleware

Supabase issues RS256 JWTs. Python verification uses `python-jose` with JWKS fetched from the Supabase project endpoint (per Supabase docs). FastAPI dependency:

```python
# Pseudocode for apps/api/services/auth.py
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Extract and verify Supabase JWT. Returns user_id (UUID string)."""
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,  # from env, or JWKS
            algorithms=["HS256"],  # Supabase default is HS256 with JWT secret
            audience="authenticated",
        )
        return payload["sub"]  # Supabase user ID
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
```

Note: Supabase uses **HS256** by default with the JWT secret from the project settings. The JWKS/RS256 approach is for custom setups. HS256 with `SUPABASE_JWT_SECRET` is simpler and is what most Supabase+FastAPI tutorials use. The planner should confirm which approach fits — HS256 is simpler, RS256 is more standard but requires JWKS caching.

### Build Order

1. **Encryption service** (`apps/api/services/encryption.py` + tests) — Zero external service dependencies. Pure crypto code. Can test in complete isolation with `pytest`. Proves D054 envelope encryption round-trip works. Unblocks key management endpoints.

2. **SQL migration files** (`apps/api/migrations/001_initial_schema.sql`) — Write the schema as a .sql file. This defines the contract downstream slices consume. Doesn't require a running Supabase instance for the file itself, but the RLS policies should be tested against a real Supabase project.

3. **JWT auth middleware** (`apps/api/services/auth.py` + tests) — Depends on `SUPABASE_JWT_SECRET` env var. FastAPI dependency that all protected endpoints will use. Testable with crafted JWTs without a running Supabase instance.

4. **Database connection layer** (`apps/api/services/database.py`) — Async connection pool to Supabase Postgres. Thin wrapper over asyncpg or psycopg async.

5. **Key management endpoints** (`apps/api/routers/keys.py` + tests) — Integrates encryption service + database + auth middleware. Four endpoints per boundary map. Testable with mocked DB.

6. **Wire auth middleware into main.py** — Add `get_current_user` dependency to the app. New endpoints are protected by default; existing S01 endpoints stay unprotected for now (S05 refactors them).

### Verification Approach

- `python -m pytest apps/api/tests/test_encryption.py -v` — Encryption round-trip: encrypt → decrypt returns original. Wrong KEK raises. Different calls produce different nonces. Empty string and long strings work.
- `python -m pytest apps/api/tests/test_auth.py -v` — Valid JWT returns user_id. Expired JWT returns 401. Missing Authorization header returns 403. Malformed token returns 401.
- `python -m pytest apps/api/tests/test_keys_endpoints.py -v` — POST stores key (encrypted, not plaintext in DB). GET status returns provider connection state without exposing values. DELETE removes key. POST verify tests connectivity.
- `python -m pytest tests/ -q` — CLI tests still pass (425).
- `python -m pytest apps/api/tests/ -v` — All API tests pass (S01 31 + S02 new tests).

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| AES-GCM authenticated encryption | `cryptography.hazmat.primitives.ciphers.aead.AESGCM` | Standard, audited, handles nonce+tag correctly. No IV/padding footguns. |
| JWT decode + verification | `python-jose` (`jose.jwt.decode`) | Supabase docs recommend it for Python. Handles HS256/RS256, expiry, audience, issuer claims. |
| FastAPI bearer token extraction | `fastapi.security.HTTPBearer` | Built-in dependency that extracts `Authorization: Bearer <token>` and returns 403 if missing. |
| Async Postgres connection | `asyncpg` or `psycopg[async]` | Production-grade async Postgres drivers. asyncpg is faster; psycopg is more featureful. Either works with Supabase Postgres. |

## Constraints

- **Python 3.13** — All libraries must be compatible (cryptography, python-jose, asyncpg all support 3.13).
- **Supabase Postgres, not raw Postgres** — Schema must work with Supabase's `auth.users` table and `auth.uid()` function. RLS policies must use `to authenticated` role.
- **APP_ENCRYPTION_SECRET must be a 32-byte key** — AESGCM-256 requires exactly 32 bytes. Store base64-encoded in env var. Document generation command: `python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"`.
- **CLI untouched** — No new dependencies in `pyproject.toml`; new deps go in `apps/api/requirements.txt` only. No changes to any file outside `apps/api/` (and the new migration dir).
- **No Supabase Python client server-side** — The `supabase-py` package is for client-side use. FastAPI talks to Postgres directly (via asyncpg) and verifies JWTs with `python-jose`. The Supabase client is only needed on the Next.js frontend (S03).
- **Existing S01 tests must not break** — The 31 API tests in `apps/api/tests/` and 425 CLI tests must continue passing. New auth middleware must be opt-in (added to new endpoints only, not retrofitted to S01 endpoints in this slice).

## Common Pitfalls

- **Nonce reuse in AES-GCM** — Reusing a nonce with the same key completely breaks AES-GCM security. The encryption service must generate a fresh random nonce per encryption call. Never derive nonces deterministically.
- **Storing KEK in the database** — The `APP_ENCRYPTION_SECRET` (KEK) must be an env var, never stored in Supabase. If the DB is compromised, encrypted keys remain safe because the KEK is external.
- **RLS on screening_results** — Results reference runs via `run_id`. The RLS policy must join through `screening_runs` to check `user_id`. A direct `user_id` column on `screening_results` is an alternative that avoids the subquery but denormalizes.
- **HS256 vs RS256 for JWT verification** — Supabase projects have a JWT secret (HS256) in Settings → API. Using HS256 is simpler (no JWKS fetch, no caching, no rotation). RS256 via JWKS is more standard but adds HTTP dependency and caching complexity. HS256 is the default and appropriate for MVP.
- **Token in request body vs header** — JWTs must come via `Authorization: Bearer <token>` header, not in the request body. This is critical for the S01→S02 transition — screen/position endpoints currently embed keys in the body. S02 adds auth via header; the body key removal happens in S05.

## Open Risks

- **Supabase project setup is manual** — Creating the Supabase project, running migrations, and getting the JWT secret are manual steps. The SQL files can be version-controlled but must be applied via the Supabase Dashboard SQL editor or `supabase db push`. This is a deployment dependency, not a code risk.
- **JWT secret rotation** — If the Supabase JWT secret changes, all existing tokens become invalid. The middleware must handle this gracefully (return 401, user re-authenticates). No code risk, but operational awareness.
- **asyncpg vs psycopg[async]** — Both work. asyncpg is faster for pure Postgres; psycopg has broader ecosystem support. The planner should pick one and commit. Recommendation: asyncpg (simpler API, better performance for this use case).

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Supabase/Postgres | supabase/agent-skills@supabase-postgres-best-practices | installed |

## Sources

- Supabase JWT verification in Python uses `python-jose` with JWKS or HS256 (source: [Supabase docs — Token Validation](https://supabase.com/docs/guides/auth/tokens))
- Supabase profile table with auto-creation trigger uses `auth.uid()` and `security definer` function (source: [Supabase docs — Managing User Data](https://supabase.com/docs/guides/auth/managing-user-data))
- RLS policies use `(select auth.uid())` wrapped in subselect for performance (source: supabase-postgres-best-practices skill, security-rls-basics reference)
- AES-GCM via `AESGCM` class: `key = AESGCM.generate_key(bit_length=256)`, `nonce = os.urandom(12)`, encrypt/decrypt with optional associated data (source: [pyca/cryptography docs](https://cryptography.io/en/latest/hazmat/primitives/aead/))
