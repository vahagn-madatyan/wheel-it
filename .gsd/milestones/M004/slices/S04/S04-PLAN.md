# S04: BYOK Key Management UI

**Goal:** User navigates to Settings, manages Alpaca and Finnhub API keys (store, verify connectivity, delete), with encrypted storage via the S02 backend endpoints.
**Demo:** User goes to Settings → sees Alpaca and Finnhub provider cards with disconnected badges → enters Alpaca api_key + secret_key + selects paper/live → clicks "Save & Verify" → sees green connected badge or red error → enters Finnhub api_key → saves and verifies → can delete either provider's keys with confirmation → badges reset to disconnected.

## Must-Haves

- Status fetch on mount shows connected/disconnected badges per provider (green/red)
- Alpaca form accepts api_key, secret_key, and paper/live toggle
- Finnhub form accepts api_key
- Store flow sends sequential POST calls for Alpaca (api_key then secret_key), single POST for Finnhub
- Auto-verify after store calls POST `/api/keys/{provider}/verify` and displays result
- Delete with confirmation removes keys and re-fetches status
- Loading spinners during store/verify operations (verify takes 1-3s)
- Error alerts for failed operations (partial Alpaca store, verify failure, network errors)
- All API calls go through `apiFetch()` from `@/lib/api-client`

## Proof Level

- This slice proves: integration (frontend UI ↔ backend CRUD endpoints)
- Real runtime required: yes (browser + FastAPI + Supabase for full verification)
- Human/UAT required: yes (visual verification of badges, forms, and flows)

## Verification

- `cd apps/web && npm run build` exits 0 — all TypeScript compiles, Settings route included in output
- `python -m pytest tests/ -q` — 425 CLI tests pass unchanged (no CLI files touched)
- Visual: navigate to `/settings` while authenticated → see two provider cards with disconnected state
- Visual: enter Alpaca keys, click Save & Verify → see loading spinner → see green badge or red error
- Visual: enter Finnhub key, save and verify → same flow
- Visual: click Delete on a provider → confirmation dialog → badge resets to disconnected

## Observability / Diagnostics

- Runtime signals: `apiFetch()` errors surface as `role="alert"` divs in the UI; network failures visible in browser DevTools Network tab
- Inspection surfaces: `GET /api/keys/status` returns per-provider connection state; browser DevTools shows Authorization headers on all API calls
- Failure visibility: API error messages displayed inline per provider card; partial Alpaca store (one key stored, second fails) shows explicit error message
- Redaction constraints: Key values entered in password-type inputs; never logged or displayed after submission

## Integration Closure

- Upstream surfaces consumed: `apiFetch()` from `@/lib/api-client` (S03), `GET/POST/DELETE /api/keys/*` endpoints (S02), app shell layout with Settings route (S03)
- New wiring introduced: Settings page calls 4 backend endpoints via apiFetch() — first real frontend↔backend integration for key management
- What remains before milestone is truly usable end-to-end: S05 (screener UI needs stored keys), S06 (positions dashboard needs stored keys), S07 (deployment)

## Tasks

- [ ] **T01: Build Settings page with provider cards, key forms, and all CRUD flows** `est:40m`
  - Why: Delivers the complete key management UI — all 4 requirements (WEB-02, WEB-03, WEB-04, WEB-13) in a single page component. Backend endpoints are tested; this wires the frontend to them.
  - Files: `apps/web/src/app/(app)/settings/page.tsx`
  - Do: Replace placeholder with `'use client'` component. State for provider status, form inputs, loading/error per provider. `useEffect` fetches `GET /api/keys/status` on mount. Render Alpaca card (api_key + secret_key password inputs + paper/live toggle) and Finnhub card (api_key password input). "Save & Verify" handler: store keys via sequential POST calls (Alpaca: api_key first, then secret_key; Finnhub: single call), then auto-verify via `POST /api/keys/{provider}/verify`, update badge. Delete handler: `window.confirm()` → `DELETE /api/keys/{provider}` → re-fetch status. Green/red badges, loading spinners, error alerts matching login page patterns. All API calls via `apiFetch()`.
  - Verify: Component renders with two provider cards, forms have correct inputs, handlers make correct API calls (verifiable by code review)
  - Done when: `settings/page.tsx` contains complete key management UI with status fetch, store, verify, and delete flows for both providers

- [ ] **T02: Build verification and optional component extraction** `est:15m`
  - Why: Quality gate — confirms the Settings page compiles without type errors, the build produces the route, and CLI tests still pass. Extracts components if the file is too long.
  - Files: `apps/web/src/app/(app)/settings/page.tsx`, potentially `apps/web/src/components/provider-card.tsx`
  - Do: Run `cd apps/web && npm run build` — fix any TypeScript errors. Run `python -m pytest tests/ -q` — confirm 425 tests pass. If `settings/page.tsx` exceeds 250 lines, extract a `ProviderCard` component to `components/provider-card.tsx`. Verify Settings route appears in build output.
  - Verify: `npm run build` exits 0, `python -m pytest tests/ -q` shows 425 passed, Settings route in build output
  - Done when: Zero build errors, CLI regression passes, Settings page compiles as part of the Next.js build

## Files Likely Touched

- `apps/web/src/app/(app)/settings/page.tsx` — placeholder → full key management UI
- `apps/web/src/components/provider-card.tsx` — extracted component (only if page exceeds ~250 lines)
