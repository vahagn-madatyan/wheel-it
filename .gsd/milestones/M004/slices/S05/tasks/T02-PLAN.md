---
estimated_steps: 4
estimated_files: 2
---

# T02: Build Put Screener page with shared results table component

**Slice:** S05 — Screener UI
**Milestone:** M004

## Description

Replace the placeholder Put Screener page with a full implementation: form inputs, async polling with progress indicator, and a sortable results table. Also extract a shared `ScreenerResultsTable` component that T03 reuses for the Call Screener.

The page checks `GET /api/keys/status` on mount — if Alpaca is not connected, it shows a "connect your API keys" message linking to `/settings`. If connected, it renders a form with preset select, symbols textarea, and buying power input. On submit, it `POST`s to `/api/screen/puts` (which now requires auth via JWT — T01), polls `GET /api/screen/runs/{run_id}` every 2 seconds, shows a progress indicator, and renders results in the sortable table on completion.

All API calls use `apiFetch()` from `@/lib/api-client` (established in S03/S04). Follow the state management pattern from `apps/web/src/app/(app)/settings/page.tsx` — per-action loading/error/result state.

## Steps

1. **Create `apps/web/src/components/screener-results-table.tsx`** — a shared `'use client'` component:
   - Props: `columns: { key: string; label: string; sortable?: boolean }[]` and `data: Record<string, unknown>[]`
   - Internal state: `sortKey: string | null`, `sortDir: 'asc' | 'desc'`
   - Click a column header to sort. First click = ascending, second = descending, third = reset.
   - Render an HTML `<table>` with Tailwind classes: `w-full text-sm text-left`, header cells with `cursor-pointer` if sortable, alternating row colors (`even:bg-gray-50`).
   - Sort indicator: `▲` / `▼` next to the active sort column header.
   - Format numeric values: prices/premiums to 2 decimal places, percentages (annualized return) to 2 decimal places with `%` suffix, delta to 2 decimal places, OI as integers with comma separators, spread to 2 decimal places.
   - Export a helper type `ColumnDef = { key: string; label: string; sortable?: boolean; format?: (v: unknown) => string }` — the `format` function lets callers customize display per column.
   - Empty state: if `data` is empty array, show "No results found" message.

2. **Build `apps/web/src/app/(app)/screener/puts/page.tsx`** — full put screener page:
   - `'use client'` directive. Imports: `useState`, `useEffect`, `useCallback`, `useRef` from React. `apiFetch` from `@/lib/api-client`. `ScreenerResultsTable` and `ColumnDef` from `@/components/screener-results-table`. `ProviderStatus`, `KeyStatusResponse` from `@/components/provider-card`.
   - **Key status check on mount:** fetch `GET /api/keys/status`, find the Alpaca provider. If not connected, render a card saying "Connect your Alpaca API keys to use the screener" with a link to `/settings`. If connected, render the form.
   - **Form fields:**
     - Preset: `<select>` with options "conservative", "moderate" (default), "aggressive"
     - Symbols: `<textarea>` with placeholder "AAPL\nMSFT\nGOOG" — parsed by splitting on whitespace/newlines/commas
     - Buying Power: `<input type="number" step="100" min="1000">` — required
   - **Submit handler:**
     - Parse symbols from textarea (split, trim, filter empty, uppercase)
     - Validate at least 1 symbol and buying power > 0
     - `POST /api/screen/puts` with body `{ symbols, buying_power, preset }`
     - Store returned `run_id` in state
     - Start polling interval
   - **Polling:**
     - `useRef` for interval ID to avoid stale closures
     - `setInterval` every 2000ms: `GET /api/screen/runs/{run_id}`
     - On `status === "completed"`: clear interval, store results in state, set loading false
     - On `status === "failed"`: clear interval, store error in state, set loading false
     - On `status === "pending" | "running"`: continue polling
     - `useEffect` cleanup: clear interval on unmount
   - **Progress indicator:** when polling, show a centered div with "Screening in progress…" text and a simple CSS spinner (Tailwind `animate-spin` on a border div)
   - **Results display:** use `ScreenerResultsTable` with put-specific column definitions:
     - Symbol (sortable), Underlying (sortable), Strike (sortable, format: $xxx.xx), DTE (sortable), Premium (sortable, format: $x.xx), Delta (sortable, format: x.xx), OI (sortable, format: comma-separated int), Spread (sortable, format: x.xx), Ann. Return (sortable, format: xx.xx%)
   - **Error display:** red alert div with `role="alert"` for API errors or screening failures

3. **Define put-specific column config** as a `const PUT_COLUMNS: ColumnDef[]` array at the top of the page file (or inline). This keeps column definitions co-located with the page that uses them.

4. **Verify build** — `cd apps/web && npm run build` must exit 0 with `/screener/puts` in the output.

## Must-Haves

- [ ] `ScreenerResultsTable` component exists and exports `ColumnDef` type
- [ ] Table supports click-to-sort with visual indicator
- [ ] Put Screener page checks key status on mount and shows "connect keys" if Alpaca not connected
- [ ] Form has preset select, symbols textarea, buying power input
- [ ] Submit triggers POST → poll loop with 2s interval
- [ ] Polling cleans up on unmount (useEffect cleanup)
- [ ] Progress indicator shown during polling
- [ ] Results rendered in sortable table on completion
- [ ] Error state shown on failure
- [ ] All `apiFetch()` calls — no raw `fetch()`
- [ ] `'use client'` directive on both files
- [ ] `npm run build` passes with zero errors

## Verification

- `cd apps/web && npm run build` exits 0
- Build output includes `ƒ /screener/puts` (or equivalent route indicator)
- `grep -c "apiFetch" apps/web/src/app/\(app\)/screener/puts/page.tsx` returns ≥3 (submit, poll, key status)
- `grep "'use client'" apps/web/src/app/\(app\)/screener/puts/page.tsx apps/web/src/components/screener-results-table.tsx` — both present
- `wc -l apps/web/src/components/screener-results-table.tsx` — file exists and is non-trivial (>50 lines)

## Inputs

- `apps/web/src/lib/api-client.ts` — `apiFetch()` function that injects Bearer token from Supabase session
- `apps/web/src/components/provider-card.tsx` — exports `ProviderStatus`, `KeyStatusResponse` types for the key status check
- `apps/web/src/app/(app)/settings/page.tsx` — reference pattern for `apiFetch()` usage, state management, and error handling. The `fetchStatus` callback and `getProvider()` helper are directly reusable patterns.
- T01 output — backend now expects `POST /api/screen/puts` with body `{ symbols: string[], buying_power: number, preset: string }` (no key fields) + `Authorization: Bearer <jwt>` header. Returns `{ run_id: string, status: "pending" }`. Poll at `GET /api/screen/runs/{run_id}` returns `{ run_id, status, run_type, results, error }`.
- `apps/api/schemas.py` — `PutResultSchema` defines result fields: symbol, underlying, strike, dte, premium, delta (nullable), oi, spread, annualized_return

## Observability Impact

- **Key status gate:** Page fetches `GET /api/keys/status` on mount. If Alpaca provider not connected, the form is hidden and a "connect keys" card renders — visible in the DOM as a link to `/settings`. Future agents can verify connectivity gate via `browser_find text="Connect your Alpaca API keys"`.
- **Polling lifecycle:** Active polling is visible via the "Screening in progress…" text and spinner. Completion replaces spinner with results table. Failure renders a `role="alert"` div with error text. Network logs show `GET /api/screen/runs/{run_id}` requests at 2s intervals.
- **Results table state:** Column sort state is reflected by `▲`/`▼` indicators in header cells. Empty results show "No results found" text.
- **Error surfaces:** All API errors (key status, submit, poll) render in `role="alert"` divs with descriptive messages. No silent failures.
- **Cleanup:** Polling interval clears on unmount (useEffect return) and on terminal status (completed/failed). No memory leaks observable in browser devtools.

## Expected Output

- `apps/web/src/components/screener-results-table.tsx` — new shared component (~100-130 lines), exports `ScreenerResultsTable` and `ColumnDef`
- `apps/web/src/app/(app)/screener/puts/page.tsx` — full put screener page replacing the placeholder (~200-250 lines)
