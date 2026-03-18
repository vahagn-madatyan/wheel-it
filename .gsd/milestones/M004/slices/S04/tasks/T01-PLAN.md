---
estimated_steps: 7
estimated_files: 1
---

# T01: Build Settings page with provider cards, key forms, and all CRUD flows

**Slice:** S04 — BYOK Key Management UI
**Milestone:** M004

## Description

Replace the placeholder Settings page with a complete `'use client'` key management component. This delivers all 4 requirements assigned to S04: Alpaca key storage (WEB-02), Finnhub key storage (WEB-03), connectivity verification (WEB-04), and key deletion (WEB-13).

The backend endpoints are fully built and tested in S02 (14 endpoint tests in `test_keys_endpoints.py`). The `apiFetch()` client from S03 handles auth header injection. This task wires the frontend to those endpoints with a form-based UI matching the login/signup styling patterns.

**Relevant installed skill:** `frontend-design` — load if you want design guidance, but the established Tailwind patterns from login/signup pages should be followed for consistency.

## Steps

1. **Replace the placeholder in `apps/web/src/app/(app)/settings/page.tsx`** with a `'use client'` component. Add `"use client"` directive at the top. Import `useState`, `useEffect`, and `apiFetch` from `@/lib/api-client`.

2. **Define TypeScript interfaces** matching the API contract at the top of the file:
   - `ProviderStatus`: `{ provider: string; connected: boolean; is_paper: boolean | null; key_names: string[] }`
   - `KeyStatusResponse`: `{ providers: ProviderStatus[] }`
   - `VerifyResponse`: `{ provider: string; valid: boolean; error?: string }`
   - Component state: `providers` (ProviderStatus[]), per-provider form state (input values, loading, error, verify result)

3. **Implement status fetch on mount** — `useEffect` calls `apiFetch('/api/keys/status')`, parses JSON as `KeyStatusResponse`, stores in state. Handle fetch errors gracefully (set an error message). This runs on mount and after every mutation (store/delete).

4. **Build Alpaca provider card** — Card with heading "Alpaca" and connection badge (green "Connected" / gray "Not connected"). When not connected, show a form with:
   - `api_key` input (type="password", placeholder="ALPACA_API_KEY")
   - `secret_key` input (type="password", placeholder="ALPACA_SECRET_KEY")
   - Paper/Live toggle — use a checkbox or toggle switch, default to paper=true
   - "Save & Verify" submit button
   When connected, show the badge, the paper/live indicator, which key names are stored, a "Verify" button, and a "Delete" button.

5. **Build Finnhub provider card** — Same layout as Alpaca but simpler:
   - `api_key` input (type="password", placeholder="FINNHUB_API_KEY")
   - "Save & Verify" submit button
   When connected, show badge + "Verify" + "Delete" buttons.

6. **Implement Save & Verify handler** — On submit:
   - Set loading=true for that provider
   - **Alpaca:** Send two sequential `POST /api/keys/alpaca` calls via `apiFetch()`:
     - First: `{ key_value: apiKeyValue, key_name: "api_key", is_paper: isPaper }`
     - Second: `{ key_value: secretKeyValue, key_name: "secret_key", is_paper: isPaper }`
     - If the first succeeds but second fails, show error "Failed to store secret key — please retry" (don't silently leave partial state)
   - **Finnhub:** Send one `POST /api/keys/finnhub` call: `{ key_value: apiKeyValue, key_name: "api_key" }`
   - After store succeeds, auto-verify: `POST /api/keys/{provider}/verify` — parse response as `VerifyResponse`
   - Show verify result: green checkmark + "Connected" if valid=true, red X + error message if valid=false
   - Re-fetch status via `GET /api/keys/status` to update badges
   - Set loading=false
   - Clear form inputs on success

7. **Implement Delete handler** — On delete button click:
   - `window.confirm('Delete all stored keys for {provider}? This cannot be undone.')` — abort if cancelled
   - Set loading=true for that provider
   - `DELETE /api/keys/{provider}` via `apiFetch()`
   - Re-fetch status to update badges
   - Clear any verify result state for that provider
   - Set loading=false

**Styling constraints (match login/signup patterns from S03):**
- Use Tailwind classes consistent with the login page: `w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900` for inputs
- Error alerts: `className="p-3 rounded-md bg-red-50 border border-red-200 text-red-700 text-sm" role="alert"`
- Success state: green badge `className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"`
- Disconnected badge: gray `className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800"`
- Loading: disable buttons + show "Saving…" / "Verifying…" / "Deleting…" text
- Buttons: blue for primary (`bg-blue-600 text-white hover:bg-blue-700`), red for delete (`bg-red-50 text-red-700 hover:bg-red-100 border border-red-200`)
- Layout: page title "Settings" + subtitle, then two cards stacked vertically with `bg-white rounded-lg shadow-sm border border-gray-200 p-6` and `space-y-6` gap

**Key API contract details (from S02 schemas.py):**
- `POST /api/keys/{provider}` body: `{ key_value: string, key_name: string, is_paper?: boolean }`
- `GET /api/keys/status` response: `{ providers: [{ provider, connected, is_paper, key_names }] }`
- `DELETE /api/keys/{provider}` response: `{ status: "deleted", provider }`
- `POST /api/keys/{provider}/verify` response: `{ provider, valid, error? }`
- Valid providers: `"alpaca"`, `"finnhub"`
- Alpaca key_names: `"api_key"`, `"secret_key"` (two separate store calls)
- Finnhub key_names: `"api_key"` (one store call)
- All calls need `Content-Type: application/json` header on POST requests
- `apiFetch()` already handles the Authorization header — just pass the path and options

## Must-Haves

- [ ] `'use client'` directive at top of settings/page.tsx
- [ ] Status fetch on mount via `GET /api/keys/status` through `apiFetch()`
- [ ] Alpaca card with api_key input, secret_key input, paper/live toggle
- [ ] Finnhub card with api_key input
- [ ] Green/gray connection badges per provider
- [ ] Sequential POST for Alpaca (api_key first, secret_key second), single POST for Finnhub
- [ ] Auto-verify after store via `POST /api/keys/{provider}/verify`
- [ ] Loading spinners/disabled state during async operations
- [ ] Error alerts for failed operations (network, partial store, verify failure)
- [ ] Delete with `window.confirm()` confirmation
- [ ] Re-fetch status after every mutation (store or delete)
- [ ] All API calls via `apiFetch()` from `@/lib/api-client`

## Verification

- File exists at `apps/web/src/app/(app)/settings/page.tsx` with `'use client'` directive
- File imports `apiFetch` from `@/lib/api-client`
- File contains `useEffect` with `apiFetch('/api/keys/status')` call
- File contains handlers for store (POST), verify (POST), and delete (DELETE) operations
- Alpaca form has two password inputs and a paper/live toggle
- Finnhub form has one password input
- Green/gray badge classes present in the JSX
- Error alert pattern matches login page (`role="alert"`, `bg-red-50`)

## Inputs

- `apps/web/src/app/(app)/settings/page.tsx` — current placeholder to replace entirely
- `apps/web/src/lib/api-client.ts` — `apiFetch()` function to import and use for all API calls
- `apps/web/src/app/(auth)/login/page.tsx` — reference for Tailwind styling patterns (inputs, buttons, error alerts, loading states)
- API contract from `apps/api/schemas.py` — response shapes for key endpoints (documented in steps above)

## Expected Output

- `apps/web/src/app/(app)/settings/page.tsx` — complete `'use client'` Settings page with provider cards, forms, status badges, and all CRUD handlers (~200-300 lines)
