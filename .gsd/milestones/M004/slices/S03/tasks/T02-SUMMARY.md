---
id: T02
parent: S03
milestone: M004
provides:
  - Auth middleware that refreshes Supabase sessions and protects routes via getUser()
  - Auth callback route at /auth/callback for email confirmation code exchange
  - Login page at /login with email+password form using signInWithPassword()
  - Signup page at /signup with email+password form using signUp() and confirmation message
key_files:
  - apps/web/src/middleware.ts
  - apps/web/src/app/auth/callback/route.ts
  - apps/web/src/app/(auth)/layout.tsx
  - apps/web/src/app/(auth)/login/page.tsx
  - apps/web/src/app/(auth)/signup/page.tsx
key_decisions:
  - Middleware uses createServerClient directly (not the server.ts wrapper) because middleware needs request/response cookie handlers, not the cookies() async API
  - Auth callback route uses the server.ts wrapper since it's a route handler where cookies() works
patterns_established:
  - Middleware setAll writes cookies to BOTH request.cookies and response.cookies to avoid stale cookies in downstream server components
  - Auth pages use (auth) route group with centered card layout, no sidebar
  - Client components use createClient() from lib/supabase/client for auth operations
  - Error display uses role="alert" div with red styling for accessibility
observability_surfaces:
  - Middleware 307 redirects visible in browser Network tab and server terminal
  - Auth callback failures redirect to /login?error=auth (query param is the failure signal)
  - Login/signup errors render as role="alert" elements with Supabase error message
  - Supabase auth cookies visible in browser DevTools → Application → Cookies
duration: 15m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Implement auth middleware, callback route, and login/signup pages

**Built complete auth flow: middleware protects /dashboard, /screener/*, /settings with session-verified redirects; login and signup pages render email+password forms with error handling.**

## What Happened

Created 5 files implementing the full auth flow:

1. **Middleware** (`src/middleware.ts`): Creates a Supabase server client with dual cookie handlers (writes to both request and response), calls `getUser()` (not `getSession()`) for verified auth checks, redirects unauthenticated users from protected routes to `/login`, and redirects authenticated users from auth pages to `/dashboard`.

2. **Auth callback** (`src/app/auth/callback/route.ts`): Handles email confirmation by reading the `code` query param, exchanging it for a session via `exchangeCodeForSession()`, and redirecting to `/dashboard` on success or `/login?error=auth` on failure.

3. **Auth layout** (`src/app/(auth)/layout.tsx`): Centered card layout with `min-h-screen flex items-center justify-center` and white card container. No sidebar or app chrome.

4. **Login page** (`src/app/(auth)/login/page.tsx`): Client component with email/password form, `signInWithPassword()` call, error alert display, loading state, and link to signup.

5. **Signup page** (`src/app/(auth)/signup/page.tsx`): Client component with email/password form, `signUp()` call, success state showing "check your email" message, error alert, and link to login.

## Verification

- ✅ `cd apps/web && npm run build` — exits 0, all routes compiled (/, /_not-found, /auth/callback, /login, /signup)
- ✅ Navigate to `/dashboard` without auth → redirected to `/login` (URL shows `/login`)
- ✅ Navigate to `/screener/puts` without auth → redirected to `/login`
- ✅ Navigate to `/settings` without auth → redirected to `/login`
- ✅ Login page renders at `/login` with "Sign in to Wheeely" heading, email/password inputs, submit button
- ✅ Signup page renders at `/signup` with "Create your Wheeely account" heading, email/password inputs, submit button
- ✅ Login form shows error alert on failed sign-in (tested with placeholder Supabase URL — shows "Failed to fetch" error in red alert)
- ✅ Signup page has "Already have an account? Sign in" link; login page has "Don't have an account? Sign up" link

### Slice-level verification (partial — T02 is intermediate task):
- ✅ `cd apps/web && npm run build` — build succeeds with zero errors
- ✅ Navigate to `/dashboard` while unauthenticated — redirected to `/login`
- ⬜ Sign up with valid email → requires real Supabase project (S02 prerequisite)
- ⬜ Log in with valid credentials → requires real Supabase project
- ⬜ Sidebar visible after login → T03 (app shell)
- ⬜ Nav links render pages → T03
- ⬜ Logout redirects to /login → T03
- ⬜ apiFetch sends Bearer token → T03

## Diagnostics

- **Middleware redirects:** Visible as 307 responses in browser DevTools Network tab. Server terminal shows route being hit.
- **Cookie flow:** Check browser DevTools → Application → Cookies for `sb-*` cookies after successful auth.
- **Auth errors:** Login/signup errors render in a `[role="alert"]` div with Supabase error message text.
- **Callback failures:** Redirect to `/login?error=auth` — the query param presence indicates a failed code exchange.
- **Missing env vars:** Supabase client crashes with a console error if `NEXT_PUBLIC_SUPABASE_URL` or `NEXT_PUBLIC_SUPABASE_ANON_KEY` is missing.

## Deviations

- **Next.js 16 middleware deprecation warning:** Next.js 16.1.7 shows "The 'middleware' file convention is deprecated. Please use 'proxy' instead." The middleware still compiles and runs correctly — this is a forward-looking deprecation. No action needed for this slice; migration to the proxy convention can happen in a future task if needed.

## Known Issues

- Login/signup forms cannot be fully end-to-end tested without a real Supabase project (placeholder .env.local values cause "Failed to fetch" on auth calls). This is expected — real credentials are an S02 prerequisite.

## Files Created/Modified

- `apps/web/src/middleware.ts` — Session refresh + route protection middleware with getUser() and dual cookie handlers
- `apps/web/src/app/auth/callback/route.ts` — Email confirmation code exchange route handler
- `apps/web/src/app/(auth)/layout.tsx` — Centered card layout for auth pages
- `apps/web/src/app/(auth)/login/page.tsx` — Login form with signInWithPassword, error handling, loading state
- `apps/web/src/app/(auth)/signup/page.tsx` — Signup form with signUp, success confirmation message, error handling
- `.gsd/milestones/M004/slices/S03/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
