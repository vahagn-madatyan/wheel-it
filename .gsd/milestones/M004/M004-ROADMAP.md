# M004: Free Tier Online

**Vision:** A trader signs up, connects their Alpaca + Finnhub keys, runs put/call screeners in a browser, and sees their positions — identical to the CLI but online, multi-tenant, with encrypted key storage. CLI untouched. Premium directory structure exists but is inert.

## Success Criteria

- A new user can sign up with email, log in, and access an authenticated dashboard
- User can store Alpaca (key + secret + paper/live) and Finnhub API keys with encryption, verify connectivity, and delete them
- User can run the put screener from a browser with preset selection and see ranked results matching CLI output
- User can run the call screener from a browser with symbol + cost basis and see ranked results
- User can view their Alpaca positions with wheel state and account summary
- A second user's keys, screening results, and positions are fully isolated
- Free-tier rate limiting blocks the 4th screening run within 24 hours
- The CLI (`run-strategy`, `run-screener`, `run-put-screener`, `run-call-screener`) works exactly as before with 425 tests passing
- The app is deployed and accessible on a public Render URL

## Key Risks / Unknowns

- Per-request Alpaca/Finnhub client construction — current code uses module-level env vars; multi-tenant needs per-user client instantiation from decrypted keys without touching CLI paths
- Async screening over HTTP — CLI runs take 30-60s; API must run screening as background tasks with status polling
- Envelope encryption for API keys — storing brokerage credentials for other people's money; security-critical
- Import path stability — introducing `apps/` structure must not break CLI console scripts in `pyproject.toml`

## Proof Strategy

- Per-request client construction → retire in S01 by building FastAPI endpoints that construct Alpaca/Finnhub clients from request-provided keys and return real screening results
- Async screening → retire in S01 by implementing background task pattern (submit → poll → results) and proving 60s screening runs complete without HTTP timeout
- Envelope encryption → retire in S02 by implementing encrypt/decrypt round-trip with APP_ENCRYPTION_SECRET and verifying decrypted keys work for API calls
- Import path stability → retire in S01 by confirming `python -m pytest tests/ -q` still passes 425 tests after directory restructure

## Verification Classes

- Contract verification: pytest for API endpoints (mocked screener), auth middleware, encryption round-trip, rate limiting, frontend component tests
- Integration verification: Full vertical flow with real Supabase instance — signup, key storage, screener run, results retrieval, positions fetch
- Operational verification: Render deployment via Blueprint; service restart recovery; private network API connectivity
- UAT / human verification: User completes full free-tier flow on deployed instance; second user confirms data isolation

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 7 slices are complete with passing verification
- FastAPI serves screening results using the existing `screen_puts()` / `screen_calls()` engine
- Next.js frontend provides auth, key management, screener UI, and positions dashboard
- API keys are encrypted at rest with envelope encryption
- Rate limiting enforces 3 runs/day for free tier
- Multi-tenant isolation is proven (two users, different data)
- Deployed on Render with private networking between web and API
- CLI 425 tests still pass unchanged
- End-to-end acceptance scenario passes on the deployed instance

## Requirement Coverage

- Covers: WEB-01 through WEB-13, CLI-COMPAT-01
- Partially covers: none
- Leaves for later: PREM-01 (billing), PREM-02 (FMP), PREM-03 (ORATS), PREM-04 (auto-trading), PREM-05 (LLM), PREM-06 (trade execution), PREM-07 (watchlists), PREM-08 (journal)
- Orphan risks: none

## Slices

- [x] **S01: FastAPI wraps existing screener engine** `risk:high` `depends:[]`
  > After this: `curl -X POST /api/screen/puts` with Alpaca+Finnhub keys returns JSON put recommendations from the real screening engine running as a background task. `curl GET /api/screen/runs/{id}` polls for completion. `curl GET /api/positions` returns positions. 425 CLI tests still pass. Verified by API tests with mocked screener + one live integration test.

- [x] **S02: Supabase auth + database + encrypted key storage** `risk:high` `depends:[]`
  > After this: Supabase project has `profiles`, `api_keys`, `screening_runs`, `screening_results` tables with RLS. FastAPI auth middleware verifies Supabase JWTs. API keys encrypt/decrypt round-trip via envelope encryption. Verified by auth tests, encryption round-trip tests, and RLS policy tests against real Supabase.

- [x] **S03: Next.js shell + auth flow** `risk:medium` `depends:[S02]`
  > After this: User visits the app in a browser, signs up with email, logs in, sees an authenticated app shell with sidebar nav (Dashboard, Put Screener, Call Screener, Settings). Logout works. Unauthenticated users are redirected to login. Verified in browser against running dev server.

- [x] **S04: BYOK key management UI** `risk:medium` `depends:[S02, S03]`
  > After this: User navigates to Settings, enters Alpaca key+secret with paper/live toggle and Finnhub key. Keys are stored encrypted via the API. Connection status shows green/red badges after verification. User can delete keys. Verified in browser with real key storage and connectivity check.

- [ ] **S05: Screener UI** `risk:medium` `depends:[S01, S04]`
  > After this: User navigates to Put Screener, selects a preset, enters symbols and buying power, clicks Run. Progress indicator shows while background task runs. Results appear in a sortable table matching CLI columns (symbol, strike, DTE, premium, delta, OI, spread, annualized return). Call Screener works similarly with symbol + cost basis. Verified in browser with real screener results.

- [ ] **S06: Positions dashboard + rate limiting** `risk:low` `depends:[S01, S04]`
  > After this: Dashboard shows positions table with wheel state (short_put / long_shares / short_call), account card with buying power and capital at risk. Redis rate limiting blocks the 4th screening run in 24 hours with a clear message. Verified in browser + rate limit test.

- [ ] **S07: Deployment + end-to-end verification** `risk:medium` `depends:[S01, S02, S03, S04, S05, S06]`
  > After this: App is live on Render. `render.yaml` Blueprint defines web, api, and redis services. Docker Compose works for local dev. `/premium/__init__.py` exposes tier detection (always returns "free" for now). A real user completes the full flow on the deployed instance: signup → add keys → run screener → see results → see positions. Second user confirms isolation.

## Boundary Map

### S01 → S05

Produces:
- `POST /api/screen/puts` accepting `{symbols, buying_power, preset}` body, returning `{run_id}`
- `POST /api/screen/calls` accepting `{symbol, cost_basis, preset}` body, returning `{run_id}`
- `GET /api/screen/runs/{run_id}` returning `{status, results}` where results match `PutRecommendation` / `CallRecommendation` field shapes
- `GET /api/positions` returning position list with wheel state
- `GET /api/account` returning buying power, capital at risk

Consumes:
- nothing (first slice)

### S01 → S06

Produces:
- `GET /api/positions` and `GET /api/account` endpoints
- Background task infrastructure (task submission, status polling)

### S02 → S03

Produces:
- Supabase project with auth configured (email provider)
- `profiles` table auto-populated on signup via trigger
- JWT verification middleware for FastAPI
- Supabase client config (URL + anon key) for frontend

### S02 → S04

Produces:
- `api_keys` table with envelope encryption columns (encrypted_key, encrypted_dek, key_nonce)
- `POST /api/keys/{provider}` endpoint for storing encrypted keys
- `GET /api/keys/status` endpoint returning connection status per provider (no values)
- `DELETE /api/keys/{provider}` endpoint
- `POST /api/keys/{provider}/verify` endpoint testing key validity
- Key decryption utility for use by screening endpoints

### S03 → S04

Produces:
- Authenticated app shell with route protection
- Settings page route (`/settings`)
- API client with auth token injection

### S03 → S05

Produces:
- App shell with Put Screener and Call Screener routes
- Authenticated API client

### S04 → S05

Produces:
- User has stored Alpaca + Finnhub keys (prerequisite for screening)
- Key status available to screener UI (can show "connect keys first" if missing)

### S04 → S06

Produces:
- User has stored Alpaca keys (prerequisite for positions/account fetch)

### S01-S06 → S07

Produces:
- All API endpoints, auth, frontend pages, rate limiting — working locally
- Docker Compose for local dev environment

Consumes:
- Everything from S01-S06 assembled into deployable services
