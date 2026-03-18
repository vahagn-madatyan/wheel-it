# S05 ("Screener UI") — Research

**Date:** 2026-03-17

## Summary

S05 replaces the two placeholder screener pages (`/screener/puts` and `/screener/calls`) with working forms that submit screening runs, poll for completion, and render sortable results tables matching the CLI columns. It also requires a **backend update**: the `screen.py` and `positions.py` routers still accept raw API keys in request bodies (S01 pattern). Since the frontend doesn't have key values — they're encrypted in the DB — the endpoints must be updated to use `get_current_user` + key retrieval/decryption from the `api_keys` table, exactly as `keys.py` verify already does.

The work is straightforward: the auth pattern (`Depends(get_current_user)` + `Depends(get_db)` → decrypt) is established in `apps/api/routers/keys.py:162-206`. The frontend polling + table rendering is standard React state management using the `apiFetch()` client from S03/S04.

## Recommendation

Build backend-first: update `screen.py` and `positions.py` to use auth + stored keys, then build the two frontend pages. The backend change is the riskier piece (modifies working endpoints, needs updated tests). The frontend is pure additive work against a known API contract.

## Implementation Landscape

### Key Files

- `apps/api/routers/screen.py` — Currently accepts `AlpacaKeysMixin` fields in POST bodies. Must switch to `Depends(get_current_user)` + key retrieval from DB. The `PutScreenRequest` and `CallScreenRequest` schemas lose the key fields and keep only screening params.
- `apps/api/routers/positions.py` — Same issue: accepts keys as query params. Must switch to auth + stored keys.
- `apps/api/schemas.py` — `PutScreenRequest`, `CallScreenRequest`, `PositionsQuery`, `AccountQuery` currently extend `AlpacaKeysMixin`. New auth-aware schemas replace these (remove key fields, keep screening params only).
- `apps/api/tests/test_screen_endpoints.py` — 11 tests need updating: mock auth + mock DB instead of passing keys in request bodies.
- `apps/api/tests/test_positions_account.py` — 8 tests need updating: same pattern.
- `apps/web/src/app/(app)/screener/puts/page.tsx` — Placeholder → full put screener page: preset select, symbols textarea, buying power input, submit button, polling state, results table.
- `apps/web/src/app/(app)/screener/calls/page.tsx` — Placeholder → full call screener page: symbol input, cost basis input, preset select, submit button, polling state, results table.

### Patterns to Follow

**Backend auth + key retrieval** — Copy the exact pattern from `apps/api/routers/keys.py:162-206` (the `verify_keys` endpoint):
```
user_id = Depends(get_current_user)
db = Depends(get_db)
rows = await db.fetch("SELECT ... FROM api_keys WHERE user_id = $1 AND provider = $2", user_id, "alpaca")
decrypt each row → build client via create_alpaca_clients()
```

**Frontend form + polling** — Copy the `apiFetch()` + state pattern from `apps/web/src/app/(app)/settings/page.tsx`:
- `'use client'` directive
- `useState` for form inputs, loading, error, results
- `apiFetch('/api/screen/puts', { method: 'POST', body: ... })` → get `run_id`
- `setInterval` poll `apiFetch('/api/screen/runs/{run_id}')` until `status === 'completed'` or `'failed'`
- Render results in an HTML table with Tailwind classes matching existing card/badge styling

**Key status check** — Screener pages should check `GET /api/keys/status` on mount. If Alpaca is not connected, show a "connect your API keys" message linking to `/settings` instead of the form. The `ProviderStatus` type is already exported from `apps/web/src/components/provider-card.tsx`.

### Build Order

1. **Backend: auth-aware screening endpoints** — Update `screen.py` to use `Depends(get_current_user)` + key retrieval from DB. Update `positions.py` the same way. Update schemas (remove `AlpacaKeysMixin` from screen/position schemas, keep only screening params). Update all API tests to mock auth + DB. This unblocks the frontend — without it, the frontend has no way to call the screener (it doesn't have raw keys).

2. **Frontend: Put Screener page** — Replace placeholder with form (preset `<select>`, symbols `<textarea>`, buying power `<input type="number">`), submit handler, polling loop with progress indicator, results table with all CLI columns (symbol, underlying, strike, DTE, premium, delta, OI, spread, ann. return), sortable by clicking column headers.

3. **Frontend: Call Screener page** — Same pattern as puts but simpler form (symbol `<input>`, cost basis `<input type="number">`, preset `<select>`). Results table has same columns plus `cost_basis`. Can reuse table rendering logic — consider extracting a shared `ResultsTable` component if both tables are identical except for the `cost_basis` column.

### Column Definitions (from CLI)

**Put Screener columns:** Symbol, Underlying, Strike, DTE, Premium, Delta, OI, Spread, Ann. Return
**Call Screener columns:** Symbol, Strike, DTE, Premium, Delta, OI, Spread, Ann. Return (plus Cost Basis in the data)

These match `PutResultSchema` and `CallResultSchema` in `apps/api/schemas.py`.

### API Contract Changes

**PUT screening (before → after):**
- Before: `POST /api/screen/puts` body = `{alpaca_api_key, alpaca_secret_key, is_paper, symbols, buying_power, preset}`
- After: `POST /api/screen/puts` body = `{symbols, buying_power, preset}` + `Authorization: Bearer <jwt>`

**CALL screening (before → after):**
- Before: `POST /api/screen/calls` body = `{alpaca_api_key, alpaca_secret_key, is_paper, symbol, cost_basis, preset}`
- After: `POST /api/screen/calls` body = `{symbol, cost_basis, preset}` + `Authorization: Bearer <jwt>`

**Positions/Account (before → after):**
- Before: `GET /api/positions?alpaca_api_key=...&alpaca_secret_key=...&is_paper=true`
- After: `GET /api/positions` + `Authorization: Bearer <jwt>`
- Same for `GET /api/account`

**Polling endpoint unchanged:** `GET /api/screen/runs/{run_id}` — no keys involved, no change needed (though it should gain auth to prevent cross-user polling).

### Verification Approach

1. `python -m pytest apps/api/tests/ -v` — all API tests pass with auth-aware endpoints
2. `python -m pytest tests/ -q` — 425 CLI tests still pass
3. `cd apps/web && npm run build` — zero TypeScript errors, both screener routes in build output
4. Visual check: navigate to `/screener/puts` and `/screener/calls` — form renders, "connect keys" state works when keys missing

## Constraints

- `screen_puts()` and `screen_calls()` only need Alpaca clients — no Finnhub keys. But key status check should verify Alpaca is connected (required) and optionally Finnhub (nice-to-have warning).
- `AlpacaKeysMixin` is used by 4 schemas — removing it from screen/position schemas must not break the `KeyStoreRequest` which doesn't use it (it's independent).
- The `create_alpaca_clients()` factory returns `(TradingClient, OptionHistoricalDataClient, StockHistoricalDataClient)` — order matters. The screen router passes `(trade_client, option_client, ...)` while the function returns `(trade, option, stock)`. Current code in `screen.py:52` destructures correctly: `trade_client, option_client, stock_client = create_alpaca_clients(...)`.
- Tailwind v4 with `@import "tailwindcss"` — no `tailwind.config.js`. All utility classes available by default.

## Common Pitfalls

- **Polling interval too aggressive** — `setInterval(fn, 1000)` is fine for MVP but must be cleared on unmount and on completion. Use `useEffect` cleanup to avoid memory leaks and stale polls.
- **AlpacaKeysMixin removal scope** — `AlpacaKeysMixin` is used by `PutScreenRequest`, `CallScreenRequest`, `PositionsQuery`, `AccountQuery`. Removing it from these 4 must not touch `KeyStoreRequest` (separate schema). Best approach: create new auth-aware request models that omit keys, deprecate the old ones.
- **is_paper flag retrieval** — When decrypting keys from DB, the `is_paper` flag is stored per-row in `api_keys` table. The verify endpoint already reads `row["is_paper"]` — same pattern needed in screen endpoints.
