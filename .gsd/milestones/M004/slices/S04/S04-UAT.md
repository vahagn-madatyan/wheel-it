# S04: BYOK Key Management UI — UAT

**Milestone:** M004
**Written:** 2026-03-17

## UAT Type

- UAT mode: mixed (artifact-driven + live-runtime)
- Why this mode is sufficient: Build/compile checks verify TypeScript correctness and CLI compatibility. Live-runtime tests verify the actual key management flows (store, verify, delete) require browser + FastAPI + Supabase.

## Preconditions

1. FastAPI server running at `http://localhost:8000` with valid `DATABASE_URL`, `SUPABASE_JWT_SECRET`, and `APP_ENCRYPTION_SECRET` env vars
2. Next.js dev server running at `http://localhost:3000` with `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, and `NEXT_PUBLIC_API_URL=http://localhost:8000` env vars
3. Supabase instance with `api_keys` table and RLS policies from S02
4. A registered user account (from S03 signup flow)
5. Valid Alpaca paper trading API key + secret (free to create at alpaca.markets)
6. Valid Finnhub API key (free at finnhub.io)

## Smoke Test

Log in → navigate to `/settings` → see two provider cards (Alpaca and Finnhub) with gray "Not connected" badges → page loads without errors.

## Test Cases

### 1. Initial state shows disconnected providers

1. Log in to the app
2. Navigate to `/settings`
3. **Expected:** Page title "Settings" visible. Two provider cards visible: "Alpaca" and "Finnhub". Both show gray "Not connected" badges. Alpaca card shows two password inputs (API Key, Secret Key) and a paper/live toggle defaulted to "Paper trading". Finnhub card shows one password input (API Key). Both cards show "Save & Verify" buttons.

### 2. Store and verify Alpaca keys (paper mode)

1. On the Settings page, enter a valid Alpaca paper API key in the "API Key" field
2. Enter the corresponding secret key in the "Secret Key" field
3. Confirm the paper toggle shows "Paper trading"
4. Click "Save & Verify"
5. **Expected:** Button text changes to "Saving…" with disabled state. After 1-3 seconds, a green banner appears: "✓ Alpaca keys verified — connection is working". The badge changes to green "Connected" with a yellow "Paper" badge. The form is replaced by "Stored keys: api_key, secret_key" text with "Verify" and "Delete" buttons.

### 3. Store and verify Finnhub key

1. Enter a valid Finnhub API key in the Finnhub card's "API Key" field
2. Click "Save & Verify"
3. **Expected:** Button shows "Saving…" during operation. Green banner appears: "✓ Finnhub keys verified — connection is working". Badge changes to green "Connected". Form is replaced by stored key info with "Verify" and "Delete" buttons.

### 4. Re-verify connected Alpaca keys

1. With Alpaca keys already stored and connected, click the "Verify" button on the Alpaca card
2. **Expected:** Button text changes to "Verifying…". After 1-3 seconds, green verification banner appears confirming connection is working.

### 5. Delete Alpaca keys

1. With Alpaca keys stored and connected, click the "Delete" button on the Alpaca card
2. A browser confirmation dialog appears: "Delete all stored keys for Alpaca? This cannot be undone."
3. Click "OK" to confirm
4. **Expected:** Badge reverts to gray "Not connected". Paper badge disappears. The form with password inputs and paper toggle reappears. No error messages.

### 6. Delete Finnhub key

1. With Finnhub key stored and connected, click the "Delete" button
2. Confirm the browser dialog
3. **Expected:** Badge reverts to "Not connected". Key entry form reappears.

### 7. Cancel delete confirmation

1. With a provider connected, click "Delete"
2. Click "Cancel" on the browser confirmation dialog
3. **Expected:** Nothing changes — badge stays green, stored keys remain displayed.

### 8. Alpaca live mode toggle

1. With Alpaca disconnected, uncheck the paper toggle so it shows "Live trading"
2. Enter valid Alpaca live API key + secret
3. Click "Save & Verify"
4. **Expected:** After verification, Alpaca card shows green "Connected" badge with a blue "Live" badge (not yellow "Paper").

## Edge Cases

### Invalid Alpaca keys

1. Enter incorrect/invalid Alpaca API key and secret key
2. Click "Save & Verify"
3. **Expected:** Keys are stored (POST succeeds), but verification fails. Red banner appears: "✗ Verification failed: [error message from backend]". Badge may show "Connected" (keys stored) but verify result clearly shows the failure.

### Invalid Finnhub key

1. Enter an invalid Finnhub API key (e.g., "invalid-key-12345")
2. Click "Save & Verify"
3. **Expected:** Similar to invalid Alpaca — store succeeds, verify fails with red error banner.

### Empty fields

1. Leave all fields empty and click "Save & Verify"
2. **Expected:** Browser's native HTML validation prevents form submission (fields have `required` attribute). No API call made.

### Partial Alpaca key entry

1. Enter only the API Key field, leave Secret Key empty
2. Click "Save & Verify"
3. **Expected:** HTML validation prevents submission — Secret Key field is required.

### Network error during save

1. Stop the FastAPI server
2. Try to save keys
3. **Expected:** Red error alert appears with a network error message (e.g., "Failed to fetch" or similar). Badge remains "Not connected".

### Status fetch failure on page load

1. Stop the FastAPI server, then navigate to `/settings`
2. **Expected:** Red alert banner at top of page: "Failed to load key status" or similar. Provider cards still render but without connection status data.

### Partial Alpaca store failure

1. With backend running, simulate a scenario where the first POST (api_key) succeeds but the second POST (secret_key) fails (e.g., by temporarily making the endpoint reject the second call)
2. **Expected:** Red error alert: "Failed to store secret key — please retry". The api_key may be stored, but the user is clearly told to retry.

## Failure Signals

- Provider cards don't render → Settings page component failed to compile or mount
- Badges always show "Not connected" after saving valid keys → `GET /api/keys/status` endpoint not returning data, or response shape mismatch
- "Save & Verify" button stays in "Saving…" state indefinitely → API call hanging, check FastAPI server logs and network tab
- No confirmation dialog on delete → `window.confirm()` call missing
- Console errors about `apiFetch` → auth token not being injected, check Supabase session
- 401 errors on API calls → JWT token expired or middleware rejecting, check `Authorization: Bearer <token>` header in network tab
- Green badge appears but no Paper/Live badge for Alpaca → `is_paper` field not being returned from status endpoint

## Requirements Proved By This UAT

- WEB-02 — User stores Alpaca api_key + secret_key + paper/live toggle (test cases 2, 8)
- WEB-03 — User stores Finnhub api_key (test case 3)
- WEB-04 — User verifies API key connectivity with green/red result (test cases 2, 3, 4)
- WEB-13 — User deletes stored API keys (test cases 5, 6, 7)

## Not Proven By This UAT

- Encryption at rest — keys are encrypted by S02 backend, not directly visible in this UI-focused UAT. Verified by S02 encryption round-trip tests.
- Multi-tenant isolation — would require a second user session. Covered by S02 RLS policies and tested in S07 end-to-end.
- Rate limiting — not applicable to key management, covered by S06.
- Mobile/responsive layout — not tested in this UAT.

## Notes for Tester

- Use Alpaca **paper** trading keys for safety (free at https://app.alpaca.markets/paper/dashboard/overview)
- Use a free Finnhub key (free at https://finnhub.io/register)
- The paper/live toggle defaults to "Paper trading" — this is intentional for safety
- The `middleware` deprecation warning in the Next.js console is a known Next.js 16 issue and does not affect functionality (see KNOWLEDGE.md)
- After deleting keys, you can immediately re-add them — there's no cooldown
- Verification calls (POST /verify) may take 1-3 seconds because they make real API calls to Alpaca/Finnhub
