---
estimated_steps: 5
estimated_files: 5
---

# T02: Implement auth middleware, callback route, and login/signup pages

**Slice:** S03 — Next.js shell + auth flow
**Milestone:** M004

## Description

Build the complete auth flow: Next.js middleware that refreshes Supabase sessions and protects routes, the auth callback route for email confirmation, and login/signup pages with email+password forms. This is the core of S03 — after this task, unauthenticated users are blocked from the app and can sign up or log in.

**Skills to load:** `nextjs-supabase-auth` (at `~/.agents/skills/nextjs-supabase-auth/SKILL.md`), `nextjs-app-router-patterns` (at `~/.agents/skills/nextjs-app-router-patterns/SKILL.md`).

**Key constraints from research:**
- `@supabase/ssr` requires `getAll`/`setAll` cookie handlers (NOT the deprecated `get`/`set`/`remove` pattern)
- `getUser()` must be used for auth checks (NOT `getSession()` which reads unverified cookie data)
- Middleware's `setAll` must write cookies to BOTH request and response objects to avoid stale cookies in downstream server components
- Next.js 15 makes `cookies()` async — must `await cookies()` before using

## Steps

1. **Create the middleware** — Create `apps/web/src/middleware.ts`:
   - Import `createServerClient` from `@supabase/ssr` and `NextResponse` from `next/server`
   - In the `middleware(request)` function:
     - Create a `NextResponse.next()` response object
     - Create a Supabase server client with cookie handlers that read from `request.cookies.getAll()` and write to BOTH `request.cookies.set(...)` and `response.cookies.set(...)` in the `setAll` handler
     - Call `await supabase.auth.getUser()` to refresh the session (this is the verified check, not `getSession()`)
     - If no user and the path starts with `/dashboard`, `/screener`, or `/settings` → redirect to `/login`
     - If user exists and the path is `/login` or `/signup` → redirect to `/dashboard`
     - Return the response
   - Export `config` with `matcher` that excludes `_next/static`, `_next/image`, `favicon.ico`, and other static assets:
     ```typescript
     export const config = {
       matcher: [
         '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
       ],
     }
     ```

2. **Create the auth callback route** — Create `apps/web/src/app/auth/callback/route.ts`:
   - This handles Supabase email confirmation redirects (`/auth/callback?code=...`)
   - Read the `code` query parameter from the request URL
   - If `code` exists: create a Supabase server client (use the server utility from `lib/supabase/server.ts`), call `await supabase.auth.exchangeCodeForSession(code)`
   - Redirect to `/dashboard` on success, or `/login?error=auth` on failure
   - If no `code` param, redirect to `/login`

3. **Create the auth layout** — Create `apps/web/src/app/(auth)/layout.tsx`:
   - A simple centered layout for the auth pages (no sidebar, no app chrome)
   - Use Tailwind to center content vertically and horizontally: `min-h-screen flex items-center justify-center bg-gray-50`
   - Wrap children in a card-like container: `w-full max-w-md p-8 bg-white rounded-lg shadow-md`

4. **Create the login page** — Create `apps/web/src/app/(auth)/login/page.tsx`:
   - Add `'use client'` directive (needs browser interactivity for form submission)
   - Import `createClient` from `@/lib/supabase/client`
   - State: `email`, `password`, `error`, `loading`
   - On form submit: call `supabase.auth.signInWithPassword({ email, password })`
   - On error: show the error message in a red alert
   - On success: `router.push('/dashboard')` and call `router.refresh()` to update server components
   - Include heading "Sign in to Wheeely", email input, password input, submit button "Sign in"
   - Link at bottom: "Don't have an account? Sign up" linking to `/signup`
   - Style with Tailwind — clean, minimal form with proper spacing

5. **Create the signup page** — Create `apps/web/src/app/(auth)/signup/page.tsx`:
   - Add `'use client'` directive
   - Import `createClient` from `@/lib/supabase/client`
   - State: `email`, `password`, `error`, `loading`, `success`
   - On form submit: call `supabase.auth.signUp({ email, password })`
   - On success: set `success = true`, show "Check your email for a confirmation link" message
   - On error: show the error message in a red alert
   - Include heading "Create your Wheeely account", email input, password input, submit button "Sign up"
   - Link at bottom: "Already have an account? Sign in" linking to `/login`
   - Style consistently with the login page

## Must-Haves

- [ ] Middleware refreshes Supabase session on every request via `getUser()` (NOT `getSession()`)
- [ ] Middleware redirects unauthenticated users from `/dashboard`, `/screener/*`, `/settings` to `/login`
- [ ] Middleware redirects authenticated users from `/login`, `/signup` to `/dashboard`
- [ ] Middleware's `setAll` writes cookies to both request AND response objects
- [ ] Auth callback route exchanges `code` param for session via `exchangeCodeForSession()`
- [ ] Login page has email + password form that calls `signInWithPassword()` and redirects to `/dashboard`
- [ ] Signup page has email + password form that calls `signUp()` and shows "check email" message
- [ ] `npm run build` succeeds with zero errors

## Verification

- `cd apps/web && npm run build` — exits 0
- Navigate to `/dashboard` without auth → redirected to `/login`
- Navigate to `/screener/puts` without auth → redirected to `/login`
- Navigate to `/settings` without auth → redirected to `/login`
- Login page renders with email/password form at `/login`
- Signup page renders with email/password form at `/signup`
- Login form shows error on invalid credentials
- Signup form shows "check email" message on success

## Observability Impact

- **Middleware redirects:** Unauthenticated requests to `/dashboard`, `/screener/*`, `/settings` produce 307 redirects visible in the browser Network tab and the Next.js server terminal.
- **Auth callback errors:** Failed `exchangeCodeForSession()` calls redirect to `/login?error=auth` — the `error` query param is the observable failure signal.
- **Login/signup errors:** Client-side error state renders a red alert with the Supabase error message — visible in the DOM and via browser accessibility tree.
- **Cookie flow:** Middleware writes Supabase auth cookies on every request. Inspect via browser DevTools → Application → Cookies to verify session refresh is happening.
- **Missing env vars:** If `NEXT_PUBLIC_SUPABASE_URL` or `NEXT_PUBLIC_SUPABASE_ANON_KEY` is unset, the Supabase client constructor throws at runtime — visible as a console error and a white-screen crash.

## Inputs

- `apps/web/src/lib/supabase/client.ts` — browser client from T01
- `apps/web/src/lib/supabase/server.ts` — server client from T01
- `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` env vars (from `.env.local`)
- Supabase project has email auth provider enabled (S02 prerequisite)

## Expected Output

- `apps/web/src/middleware.ts` — session refresh + route protection
- `apps/web/src/app/auth/callback/route.ts` — email confirmation code exchange
- `apps/web/src/app/(auth)/layout.tsx` — centered card layout for auth pages
- `apps/web/src/app/(auth)/login/page.tsx` — login form with signInWithPassword
- `apps/web/src/app/(auth)/signup/page.tsx` — signup form with signUp + confirmation message
