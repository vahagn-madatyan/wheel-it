---
estimated_steps: 4
estimated_files: 3
---

# T02: Build verification and optional component extraction

**Slice:** S04 — BYOK Key Management UI
**Milestone:** M004

## Description

Quality gate task — confirms the Settings page from T01 compiles without TypeScript errors, the Next.js build includes the Settings route, and CLI tests still pass (no CLI regressions). If the Settings page exceeds ~250 lines, extract a reusable `ProviderCard` component.

## Steps

1. **Run Next.js build** — `cd apps/web && npm run build`. Check exit code is 0. If there are TypeScript errors, fix them in `settings/page.tsx`. Confirm the Settings route (`/settings`) appears in the build output route list.

2. **Run CLI test suite** — `python -m pytest tests/ -q` from the project root. Confirm 425 tests pass. This verifies no CLI files were accidentally modified.

3. **Check file length** — Count lines in `apps/web/src/app/(app)/settings/page.tsx`. If it exceeds ~250 lines, extract the provider card rendering into a separate `ProviderCard` component:
   - Create `apps/web/src/components/provider-card.tsx` as a `'use client'` component
   - Accept props: `provider` (name), `status` (connected/paper/key_names), form fields, handlers (onSave, onVerify, onDelete)
   - Move card rendering + form + badges into the component
   - Import and use in `settings/page.tsx` — should reduce it to state management + two `<ProviderCard>` renders
   - Re-run `npm run build` after extraction to confirm no type errors introduced

4. **Final verification** — Confirm both checks pass cleanly:
   - `cd apps/web && npm run build` → exit 0, `/settings` in route output
   - `python -m pytest tests/ -q` → 425 passed

## Must-Haves

- [ ] `npm run build` exits 0 with zero TypeScript errors
- [ ] Settings route `/settings` appears in build output
- [ ] `python -m pytest tests/ -q` shows 425 passed
- [ ] If page exceeds ~250 lines, ProviderCard component is extracted

## Verification

- `cd apps/web && npm run build` exits with code 0
- Build output includes `/settings` route
- `python -m pytest tests/ -q` prints "425 passed"
- If extracted: `apps/web/src/components/provider-card.tsx` exists and build still passes

## Inputs

- `apps/web/src/app/(app)/settings/page.tsx` — complete Settings page from T01
- `apps/web/package.json` — npm scripts for build
- `tests/` — CLI test suite (should be untouched, just run for regression)

## Expected Output

- `apps/web/src/app/(app)/settings/page.tsx` — confirmed compiling, possibly refactored if too long
- `apps/web/src/components/provider-card.tsx` — extracted component (only if page exceeded ~250 lines)
- Build passes, CLI tests pass — slice verification complete
