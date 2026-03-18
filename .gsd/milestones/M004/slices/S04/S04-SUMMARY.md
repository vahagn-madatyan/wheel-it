---
id: S04
parent: M004
milestone: M004
provides:
  - Complete Settings page with Alpaca and Finnhub provider cards (store, verify, delete)
  - Extracted ProviderCard component with FormField/extraFormContent pattern for reuse
  - First real frontend↔backend integration — UI wired to 4 S02 key management endpoints via apiFetch()
requires:
  - slice: S02
    provides: api_keys table with envelope encryption, POST/GET/DELETE /api/keys/* endpoints, POST /api/keys/{provider}/verify
  - slice: S03
    provides: Authenticated app shell with /settings route, apiFetch() with Bearer token injection
affects:
  - S05
  - S06
key_files:
  - apps/web/src/app/(app)/settings/page.tsx
  - apps/web/src/components/provider-card.tsx
key_decisions:
  - Extracted ProviderCard with FormField array + extraFormContent slot — card handles rendering, page owns state and handlers
  - Sequential POST for Alpaca (api_key first, then secret_key) with explicit partial-failure error messaging
  - Auto-verify after store — saves user a click and immediately confirms key validity
patterns_established:
  - Per-provider form state pattern (loading, error, verifyResult) for independent async operations on the same page
  - Composable ProviderCard with FormField[] config and extraFormContent slot for provider-specific UI (Alpaca paper toggle)
  - Shared types (ProviderStatus, VerifyResponse, ProviderFormState, KeyStatusResponse) exported from component module
observability_surfaces:
  - GET /api/keys/status is the single source of truth for connection state — called on mount and after every mutation
  - role="alert" divs surface API errors inline per provider card
  - Partial Alpaca store failure shows explicit "Failed to store secret key — please retry" message
  - Key values in password-type inputs, never logged or displayed post-submission
drill_down_paths:
  - .gsd/milestones/M004/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M004/slices/S04/tasks/T02-SUMMARY.md
duration: 18m
verification_result: passed
completed_at: 2026-03-17
---

# S04: BYOK Key Management UI

**Complete Settings page with Alpaca (api_key + secret_key + paper/live toggle) and Finnhub (api_key) provider cards — store, auto-verify, delete flows wired to S02 backend via apiFetch(), with extracted ProviderCard component**

## What Happened

Built the BYOK key management UI in two tasks: T01 created the full Settings page as a single `'use client'` component (521 lines), then T02 extracted the reusable `ProviderCard` component (settings page → 281 lines, component → 199 lines).

**T01** replaced the placeholder `/settings` page with complete key management flows for both providers. Alpaca accepts api_key + secret_key via password inputs and a paper/live toggle (defaults to paper). On "Save & Verify", it sends two sequential POST calls to `/api/keys/alpaca` (api_key first, then secret_key), then auto-verifies via `POST /api/keys/alpaca/verify`. If the second POST fails, the user sees an explicit "Failed to store secret key — please retry" message. Finnhub is simpler — single api_key, single POST, same auto-verify flow. Both providers show green/gray connection badges from `GET /api/keys/status` (fetched on mount and after every mutation). Delete triggers `window.confirm()` before executing. All API calls go through `apiFetch()` from `@/lib/api-client`.

**T02** extracted the card rendering, badge components, and form rendering into `ProviderCard` (`apps/web/src/components/provider-card.tsx`). The component accepts a `fields` array for configurable password inputs and an `extraFormContent` slot for provider-specific UI (used for Alpaca's paper/live toggle). Shared types (`ProviderStatus`, `KeyStatusResponse`, `VerifyResponse`, `ProviderFormState`, `FormField`) are exported from the component module for reuse.

## Verification

| # | Check | Result |
|---|-------|--------|
| 1 | `cd apps/web && npm run build` exits 0 | ✅ pass — zero TypeScript errors |
| 2 | `/settings` route in build output | ✅ pass — `ƒ /settings` present |
| 3 | `python -m pytest tests/ -q` — 425 tests | ✅ pass — 425 passed, 1 warning |
| 4 | `provider-card.tsx` exists | ✅ pass — 199 lines |
| 5 | `settings/page.tsx` under 300 lines post-extraction | ✅ pass — 281 lines |
| 6 | `'use client'` directive on both files | ✅ pass |
| 7 | All API calls via `apiFetch()` | ✅ pass — 9 apiFetch calls across handlers |
| 8 | Password inputs for all key fields | ✅ pass — 3 password inputs |
| 9 | Paper/live toggle for Alpaca | ✅ pass — checkbox with isPaper state |
| 10 | `window.confirm()` for both delete flows | ✅ pass — 2 calls |
| 11 | Green/gray connection badges | ✅ pass — bg-green-100, bg-gray-100 classes |
| 12 | Error alerts with `role="alert"` | ✅ pass — 5 alert divs |

Visual checks (navigate to /settings, key save/verify/delete flows) require running server — deferred to UAT.

## Requirements Advanced

- WEB-02 — UI now wires Alpaca key storage to backend; user can enter api_key + secret_key + paper/live toggle and store encrypted via POST
- WEB-03 — UI now wires Finnhub key storage to backend; user can enter api_key and store encrypted via POST
- WEB-04 — Auto-verify after store + standalone Verify button; green/red result banners show connectivity status
- WEB-13 — Delete button with confirmation dialog removes keys; status re-fetched after deletion

## Requirements Validated

- none — WEB-04 and WEB-13 need live UAT against running server to move to validated

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

None — implementation follows the plan exactly. T01 built the complete page, T02 extracted `ProviderCard` as specified for files exceeding 250 lines.

## Known Limitations

- Visual verification requires a running FastAPI + Supabase stack — code-level checks confirm compilation and API call correctness, but actual badge rendering and error display need UAT
- Partial Alpaca store (api_key succeeds, secret_key fails) leaves one key stored — the error message tells the user to retry, but there's no automatic rollback
- No client-side input validation beyond HTML `required` — backend validation handles format/length constraints

## Follow-ups

- none — all planned work for this slice is complete

## Files Created/Modified

- `apps/web/src/app/(app)/settings/page.tsx` — complete Settings page with Alpaca and Finnhub provider cards, state management, and handler functions (281 lines)
- `apps/web/src/components/provider-card.tsx` — extracted ProviderCard component with badges, form fields, connected/disconnected states, and shared types (199 lines)

## Forward Intelligence

### What the next slice should know
- S05 (Screener UI) and S06 (Positions Dashboard) can check key status via `GET /api/keys/status` — if `connected: false` for a provider, show a "connect keys first" message linking to `/settings`
- The `ProviderCard` pattern (FormField[] + extraFormContent slot) is reusable if future providers (FMP, ORATS) need similar cards
- All `apiFetch()` calls follow the same pattern: call → check `res.ok` → parse JSON → update state — copy this pattern for screener/positions API calls

### What's fragile
- Sequential Alpaca POST (api_key then secret_key) — if the second call fails, one key is stored without the other. The error message ("Failed to store secret key — please retry") is clear, but there's no backend transaction wrapping both calls.

### Authoritative diagnostics
- `GET /api/keys/status` returns the definitive connection state — if badges look wrong, check this endpoint first
- `role="alert"` divs in the DOM surface all error states — inspect these in browser DevTools

### What assumptions changed
- No assumptions changed — S02 endpoints and S03 apiFetch() worked exactly as specified in the boundary map
