---
id: T02
parent: S05
milestone: M004
provides:
  - ScreenerResultsTable shared component with ColumnDef type export
  - Full Put Screener page with key-status gate, form, polling, progress indicator, and sortable results
  - PUT_COLUMNS config co-located with put screener page
key_files:
  - apps/web/src/components/screener-results-table.tsx
  - apps/web/src/app/(app)/screener/puts/page.tsx
key_decisions:
  - Column format functions defined inline in PUT_COLUMNS array — keeps formatting co-located with the page that uses it rather than in the shared component
patterns_established:
  - ScreenerResultsTable accepts columns + data generically; callers define ColumnDef[] with format functions for domain-specific display
  - Key-status gate pattern — fetch /api/keys/status on mount, show "connect keys" card if Alpaca not connected, render form only when connected
  - Polling via useRef interval + useEffect cleanup — startPolling(runId) creates interval, clears on completed/failed/error/unmount
observability_surfaces:
  - Key connectivity gate visible as "Connect your Alpaca API keys" text with /settings link when Alpaca not connected
  - Polling progress visible as "Screening in progress…" text with spinner
  - Errors surface in role="alert" divs for key status, submit, and polling failures
  - Results count shown in "Results (N)" header above sortable table
  - Sort state indicated by ▲/▼ in column headers
duration: 12m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Build Put Screener page with shared results table component

**Built shared ScreenerResultsTable component (125 lines) and full Put Screener page (260 lines) with key-status gate, preset/symbols/buying-power form, POST→poll→results flow, and sortable results table.**

## What Happened

Created two files as planned:

1. **`screener-results-table.tsx`** — Generic `'use client'` table component that accepts `ColumnDef[]` (with optional `format` function per column) and `Record<string, unknown>[]` data. Supports click-to-sort with three-click cycle (asc → desc → reset), null-safe sorting that pushes nulls to end, and "No results found" empty state. Exports `ColumnDef` type for callers.

2. **`screener/puts/page.tsx`** — Full `'use client'` page replacing the placeholder. Flow: mount → fetch `GET /api/keys/status` via `apiFetch()` → if Alpaca not connected, render card with link to `/settings` → if connected, render form (preset select defaulting to "moderate", symbols textarea parsed on whitespace/commas, buying power number input with step=100 min=1000). Submit handler: parse & uppercase symbols, validate, `POST /api/screen/puts` via `apiFetch()`, start `setInterval` polling `GET /api/screen/runs/{run_id}` every 2s. Polling: useRef for interval ID, clears on completed/failed/error/unmount. Progress indicator uses Tailwind `animate-spin` div. Results rendered via `ScreenerResultsTable` with `PUT_COLUMNS` config defining formatters ($xx.xx for prices, xx.xx for delta/spread, comma-separated for OI, xx.xx% for annualized return).

Also patched T02-PLAN.md to add the missing `## Observability Impact` section as flagged in pre-flight.

## Verification

- `npm run build` exits 0 with `ƒ /screener/puts` in output
- `grep -c "apiFetch"` on put screener page returns 4 (≥3 required)
- Both files have `'use client'` directive
- `screener-results-table.tsx` is 125 lines (>50 required)
- 67 API tests pass, 425 CLI tests pass
- Slice-level grep checks for `retrieve_alpaca_keys` and `get_current_user` pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd apps/web && npm run build` | 0 | ✅ pass | 5.2s |
| 2 | `grep -c "apiFetch" apps/web/src/app/(app)/screener/puts/page.tsx` | 0 (→4) | ✅ pass | <1s |
| 3 | `grep "'use client'" ...puts/page.tsx ...screener-results-table.tsx` | 0 (both present) | ✅ pass | <1s |
| 4 | `wc -l apps/web/src/components/screener-results-table.tsx` | 0 (→125) | ✅ pass | <1s |
| 5 | `.venv/bin/python -m pytest apps/api/tests/ -v` | 0 (67 passed) | ✅ pass | 8.8s |
| 6 | `.venv/bin/python -m pytest tests/ -q` | 0 (425 passed) | ✅ pass | 1.0s |
| 7 | `grep -c "retrieve_alpaca_keys" .../screen.py .../positions.py` | 0 (3, 3) | ✅ pass | <1s |
| 8 | `grep -c "get_current_user" .../screen.py .../positions.py` | 0 (4, 3) | ✅ pass | <1s |

## Diagnostics

- **Key status gate:** Look for "Connect your Alpaca API keys" text on page to confirm gate is active. If Alpaca connected, form renders instead.
- **Polling state:** "Screening in progress…" text + spinner visible during active poll. Network tab shows `GET /api/screen/runs/{run_id}` at 2s intervals.
- **Error display:** All API errors render in `role="alert"` divs — check for red alert boxes on page.
- **Sort state:** Click any sortable column header — ▲/▼ indicator appears next to active sort column.
- **Empty results:** If screening completes with no results, table shows "No results found" message.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/web/src/components/screener-results-table.tsx` — New shared sortable table component (125 lines), exports `ScreenerResultsTable` and `ColumnDef`
- `apps/web/src/app/(app)/screener/puts/page.tsx` — Full put screener page replacing placeholder (260 lines)
- `.gsd/milestones/M004/slices/S05/tasks/T02-PLAN.md` — Added missing Observability Impact section
