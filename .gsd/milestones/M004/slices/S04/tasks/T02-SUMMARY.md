---
id: T02
parent: S04
milestone: M004
provides:
  - Extracted ProviderCard component for reuse across settings page
  - Build verification confirming Settings route compiles and CLI tests pass
key_files:
  - apps/web/src/components/provider-card.tsx
  - apps/web/src/app/(app)/settings/page.tsx
key_decisions:
  - Extracted ProviderCard with FormField/extraFormContent pattern — card handles rendering, page owns state and handlers
patterns_established:
  - Composable ProviderCard accepts fields array + extraFormContent slot for provider-specific UI (e.g., Alpaca paper toggle)
  - Shared types (ProviderStatus, VerifyResponse, ProviderFormState, KeyStatusResponse) exported from component module
observability_surfaces:
  - Build route list confirms /settings compilation — absence indicates import or type error
  - ProviderCard renders role="alert" divs for errors and verify results — same DOM surface as before extraction
duration: 6m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Build verification and optional component extraction

**Extracted ProviderCard component (521 → 281+199 lines) and verified build passes with /settings route and 425 CLI tests unchanged**

## What Happened

Settings page from T01 was 521 lines — well over the 250-line extraction threshold. Extracted card rendering, badge components, and form rendering into `apps/web/src/components/provider-card.tsx` (199 lines). The settings page now contains only state management, handler functions, and two `<ProviderCard>` renders (281 lines).

The ProviderCard component accepts a `fields` array for configurable password inputs and an `extraFormContent` slot for provider-specific UI (used for Alpaca's paper/live toggle). Shared types (`ProviderStatus`, `KeyStatusResponse`, `VerifyResponse`, `ProviderFormState`, `FormField`) are exported from the component module.

Both verification gates pass: Next.js build compiles with zero TypeScript errors and includes `/settings` in the route list, and all 425 CLI tests pass with no regressions.

## Verification

All slice-level verification checks that can be verified without a running server:

- ✅ `cd apps/web && npm run build` exits 0 — TypeScript compiles, `/settings` route in output
- ✅ `python -m pytest tests/ -q` — 425 passed (CLI unchanged)
- ✅ `provider-card.tsx` exists at `apps/web/src/components/provider-card.tsx`
- ✅ Build passes after extraction — no type errors introduced
- ⏭ Visual checks (navigate to /settings, key flows) — require running server, deferred to integration testing

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd apps/web && npm run build` (pre-extraction) | 0 | ✅ pass | 22.4s |
| 2 | `source .venv/bin/activate && python -m pytest tests/ -q` | 0 | ✅ pass | 1.3s |
| 3 | `cd apps/web && npm run build` (post-extraction) | 0 | ✅ pass | 4.3s |
| 4 | `/settings` in build route output | — | ✅ pass | — |
| 5 | `wc -l settings/page.tsx` → 281 lines (down from 521) | — | ✅ pass | — |

## Diagnostics

- **Build verification:** Run `cd apps/web && npm run build` — route list should include `ƒ /settings`
- **Component check:** `ls apps/web/src/components/provider-card.tsx` confirms extraction
- **Import chain:** `settings/page.tsx` imports from `@/components/provider-card` — if path alias breaks, build will fail with a clear import error

## Deviations

None — plan called for extraction if >250 lines, page was 521 lines, extraction performed.

## Known Issues

None.

## Files Created/Modified

- `apps/web/src/components/provider-card.tsx` — new extracted ProviderCard component with badge rendering, form fields, connected/disconnected states (199 lines)
- `apps/web/src/app/(app)/settings/page.tsx` — refactored to use ProviderCard, reduced from 521 to 281 lines
- `.gsd/milestones/M004/slices/S04/tasks/T02-PLAN.md` — added missing Observability Impact section
