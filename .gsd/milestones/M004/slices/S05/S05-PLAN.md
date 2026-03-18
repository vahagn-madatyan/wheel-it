# S05: Screener UI

**Goal:** Put and Call screener pages work end-to-end in the browser — user selects params, submits, sees polling indicator, then sortable results table. Backend endpoints use JWT auth + DB-stored keys instead of raw keys in request bodies.

**Demo:** User navigates to Put Screener, selects "moderate" preset, enters symbols and buying power, clicks Run. Progress indicator shows while background task runs. Results appear in a sortable table with columns: Symbol, Underlying, Strike, DTE, Premium, Delta, OI, Spread, Ann. Return. Call Screener works the same with symbol + cost basis inputs.

## Must-Haves

- Backend screen/positions endpoints switched from raw keys in request body to `Depends(get_current_user)` + key retrieval from DB
- Shared `retrieve_alpaca_keys()` helper encapsulates fetch + decrypt pattern from `keys.py:verify_keys`
- `PutScreenRequest` and `CallScreenRequest` schemas no longer include Alpaca key fields
- Poll endpoint (`GET /api/screen/runs/{run_id}`) requires auth
- Put Screener page: preset select, symbols textarea, buying power input, submit → poll → sortable results table
- Call Screener page: symbol input, cost basis input, preset select, submit → poll → sortable results table
- Both pages check key status on mount — show "connect keys" message if Alpaca not connected
- Polling cleans up on unmount and on completion (no memory leaks)
- All API tests updated to use mock auth + mock DB
- CLI 425 tests unaffected

## Proof Level

- This slice proves: integration
- Real runtime required: yes (browser against dev server for full verification, but compilation + API tests prove contracts)
- Human/UAT required: yes (visual verification of screener pages deferred to S07 UAT)

## Verification

- `python -m pytest apps/api/tests/ -v` — all API tests pass with auth-aware endpoints (≥19 tests)
- `python -m pytest tests/ -q` — 425 CLI tests still pass
- `cd apps/web && npm run build` — zero TypeScript errors, both screener routes in build output
- `grep -c "retrieve_alpaca_keys" apps/api/routers/screen.py apps/api/routers/positions.py` — helper used in both routers
- `grep -c "get_current_user" apps/api/routers/screen.py apps/api/routers/positions.py` — auth dependency in both routers

## Observability / Diagnostics

- Runtime signals: `retrieve_alpaca_keys` logs `keys_retrieved` on success, raises HTTPException 400 with descriptive message on missing keys
- Inspection surfaces: `GET /api/keys/status` remains the single source of truth for key connectivity; screener pages check this on mount
- Failure visibility: Missing keys → 400 "Alpaca API keys not configured"; decrypt failure → 400 "Failed to decrypt stored keys"; screening failure → poll returns `status: "failed"` with error string
- Redaction constraints: Decrypted key values never logged; only key_name and provider appear in log events

## Integration Closure

- Upstream surfaces consumed: `apps/api/services/auth.py` (get_current_user), `apps/api/services/database.py` (get_db), `apps/api/services/encryption.py` (decrypt_value), `apps/api/routers/keys.py` (pattern reference), `apps/web/src/lib/api-client.ts` (apiFetch), `apps/web/src/components/provider-card.tsx` (ProviderStatus type)
- New wiring introduced: `services/key_retrieval.py` shared helper consumed by screen.py + positions.py; `components/screener-results-table.tsx` shared component consumed by both screener pages
- What remains before the milestone is truly usable end-to-end: S06 (positions dashboard + rate limiting), S07 (deployment + end-to-end verification)

## Tasks

- [x] **T01: Switch screen + positions endpoints to auth + DB-stored keys** `est:45m`
  - Why: Frontend doesn't have raw API keys — they're encrypted in the DB. Without this change, the screener pages have no way to call the API. This is the riskier piece since it modifies working endpoints and 19 existing tests.
  - Files: `apps/api/services/key_retrieval.py`, `apps/api/routers/screen.py`, `apps/api/routers/positions.py`, `apps/api/schemas.py`, `apps/api/tests/test_screen_endpoints.py`, `apps/api/tests/test_positions_account.py`
  - Do: Create `retrieve_alpaca_keys(user_id, db)` helper in `services/key_retrieval.py` that fetches rows from `api_keys`, decrypts via `decrypt_value()`, validates both `api_key` and `secret_key` exist, and returns `(api_key, secret_key, is_paper)`. Update `screen.py` to replace `AlpacaKeysMixin` body fields with `Depends(get_current_user)` + `Depends(get_db)` + `retrieve_alpaca_keys()`. Same for `positions.py`. Update schemas: `PutScreenRequest` and `CallScreenRequest` drop `AlpacaKeysMixin` inheritance (keep only screening params). Remove `PositionsQuery` and `AccountQuery` (no longer needed). Add auth to poll endpoint. Update all 19 tests to use `mock_auth` + `mock_db` fixtures and mock `retrieve_alpaca_keys`. Add tests for missing-keys and auth-required error paths.
  - Verify: `python -m pytest apps/api/tests/ -v` (all pass) && `python -m pytest tests/ -q` (425 pass)
  - Done when: All API tests pass with auth-aware endpoints. No test references `ALPACA_KEYS` in request bodies or `ALPACA_QUERY_PARAMS` in query params for screen/positions endpoints.

- [ ] **T02: Build Put Screener page with shared results table component** `est:40m`
  - Why: Delivers WEB-05 — core free-tier value. Establishes the screener page pattern and shared results table component that T03 reuses.
  - Files: `apps/web/src/app/(app)/screener/puts/page.tsx`, `apps/web/src/components/screener-results-table.tsx`
  - Do: Create shared `ScreenerResultsTable` component: accepts column definitions + data array, renders sortable HTML table with Tailwind styling, handles sort-by-column-click with ascending/descending toggle. Build Put Screener page as `'use client'` component: fetch `GET /api/keys/status` on mount — if Alpaca not connected, show message with link to `/settings`; if connected, show form with preset `<select>` (conservative/moderate/aggressive), symbols `<textarea>`, buying power `<input type="number">`. On submit, `POST /api/screen/puts` via `apiFetch()`, get `run_id`, start `setInterval` polling `GET /api/screen/runs/{run_id}` every 2s. Show progress indicator while polling. On completed, render results via `ScreenerResultsTable`. On failed, show error. Clean up interval on unmount and completion via `useEffect` cleanup.
  - Verify: `cd apps/web && npm run build` — zero errors, `/screener/puts` in build output
  - Done when: Build passes. Put Screener page compiles with form, polling logic, and results table using shared component.

- [ ] **T03: Build Call Screener page reusing shared results table** `est:20m`
  - Why: Delivers WEB-06 — the second half of the wheel. Reuses shared component from T02.
  - Files: `apps/web/src/app/(app)/screener/calls/page.tsx`
  - Do: Build Call Screener page following the same pattern as T02's put screener. Form: symbol `<input type="text">`, cost basis `<input type="number">`, preset `<select>`. Submit via `POST /api/screen/calls`, poll same way. Use `ScreenerResultsTable` with call-specific column definitions (adds Cost Basis column). Same key status check, polling, error handling, and cleanup patterns as put screener.
  - Verify: `cd apps/web && npm run build` — zero errors, `/screener/calls` in build output
  - Done when: Build passes. Call Screener page compiles with form, polling, and results table with cost_basis column.

## Files Likely Touched

- `apps/api/services/key_retrieval.py` (new)
- `apps/api/routers/screen.py`
- `apps/api/routers/positions.py`
- `apps/api/schemas.py`
- `apps/api/tests/test_screen_endpoints.py`
- `apps/api/tests/test_positions_account.py`
- `apps/web/src/components/screener-results-table.tsx` (new)
- `apps/web/src/app/(app)/screener/puts/page.tsx`
- `apps/web/src/app/(app)/screener/calls/page.tsx`
