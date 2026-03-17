# S03: Next.js shell + auth flow

**Goal:** Users can sign up, log in, and see an authenticated app shell with sidebar navigation. Unauthenticated users are redirected to login. An API client utility injects the Supabase access token for downstream slices to call the FastAPI backend.
**Demo:** User visits the app → redirected to `/login` → navigates to `/signup` → signs up with email → logs in → sees dashboard with sidebar nav (Dashboard, Put Screener, Call Screener, Settings) → clicks nav links → placeholder pages render → clicks logout → redirected to `/login`.

## Must-Haves

- Next.js 15 App Router project in `apps/web/` with TypeScript + Tailwind CSS
- Supabase browser client (`createBrowserClient`) and server client (`createServerClient`) via `@supabase/ssr`
- Middleware at `middleware.ts` that refreshes Supabase session cookies and redirects unauthenticated users away from protected routes
- Auth callback route at `app/auth/callback/route.ts` that exchanges email confirmation codes for sessions
- Login page with email + password form using `supabase.auth.signInWithPassword()`
- Signup page with email + password form using `supabase.auth.signUp()`
- Authenticated app shell with sidebar nav: Dashboard (`/dashboard`), Put Screener (`/screener/puts`), Call Screener (`/screener/calls`), Settings (`/settings`)
- Logout button that signs out and redirects to `/login`
- `apiFetch()` utility that reads the Supabase session and injects `Authorization: Bearer <access_token>` for FastAPI calls
- `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` env vars consumed by Supabase clients

## Proof Level

- This slice proves: integration (frontend auth flow against Supabase + API client wiring)
- Real runtime required: yes (dev server + Supabase project)
- Human/UAT required: yes (browser verification of auth flow)

## Verification

- `cd apps/web && npm run build` — build succeeds with zero errors
- Visit `http://localhost:3000` — redirected to `/login`
- Navigate to `/dashboard` while unauthenticated — redirected to `/login`
- Sign up with valid email → "check your email" message shown
- Log in with valid credentials → redirected to `/dashboard`, sidebar visible
- Click each sidebar nav link → Dashboard, Put Screener, Call Screener, Settings pages render
- Click logout → redirected to `/login`
- `apiFetch('/api/keys/status')` sends `Authorization: Bearer <token>` header (visible in browser devtools network tab)

## Observability / Diagnostics

- Runtime signals: browser console errors on Supabase client init failure (missing env vars crash at runtime), middleware redirect logs in server terminal
- Inspection surfaces: browser devtools Network tab for API requests with Bearer token, Application tab for Supabase auth cookies
- Failure visibility: Supabase client throws if `NEXT_PUBLIC_SUPABASE_URL` or `NEXT_PUBLIC_SUPABASE_ANON_KEY` is missing; middleware redirects surface as 307 in Network tab
- Redaction constraints: access tokens visible only in browser devtools (not logged server-side); no PII in server logs

## Integration Closure

- Upstream surfaces consumed: Supabase project auth config (URL + anon key from S02), `apps/api/services/auth.py` (FastAPI `get_current_user` expects `Bearer <supabase_access_token>`)
- New wiring introduced in this slice: Next.js dev server on port 3000, API proxy rewrite to FastAPI on port 8000, Supabase cookie-based session management
- What remains before the milestone is truly usable end-to-end: S04 (key management UI), S05 (screener UI), S06 (positions dashboard + rate limiting), S07 (deployment)

## Tasks

- [x] **T01: Scaffold Next.js project and create Supabase client utilities** `est:30m`
  - Why: Everything depends on the project existing. The Supabase browser/server clients are consumed by middleware, auth pages, and the API client.
  - Files: `apps/web/package.json`, `apps/web/next.config.ts`, `apps/web/tsconfig.json`, `apps/web/tailwind.config.ts`, `apps/web/app/layout.tsx`, `apps/web/app/page.tsx`, `apps/web/lib/supabase/client.ts`, `apps/web/lib/supabase/server.ts`, `apps/web/.env.local.example`
  - Do: Run `npx create-next-app@latest apps/web --typescript --tailwind --app --src-dir --no-import-alias --use-npm`. Install `@supabase/ssr @supabase/supabase-js`. Create `lib/supabase/client.ts` with `createBrowserClient()` wrapper using `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY`. Create `lib/supabase/server.ts` with `createServerClient()` wrapper using `cookies()` from `next/headers` with `getAll`/`setAll` handlers. Add `next.config.ts` rewrite: `/api/:path*` → `http://localhost:8000/api/:path*` for dev proxy. Create `.env.local.example` documenting required env vars. Root `app/page.tsx` redirects to `/dashboard`.
  - Verify: `cd apps/web && npm run build` succeeds with zero errors; `npm run dev` starts on port 3000
  - Done when: `apps/web/` exists with working Next.js 15 project, both Supabase client utilities compile, and dev server starts

- [x] **T02: Implement auth middleware, callback route, and login/signup pages** `est:45m`
  - Why: Auth flow is the core of this slice — middleware protects routes, callback handles email confirmation, login/signup are the user-facing entry points. All depend on T01's Supabase clients.
  - Files: `apps/web/src/middleware.ts`, `apps/web/src/app/auth/callback/route.ts`, `apps/web/src/app/(auth)/layout.tsx`, `apps/web/src/app/(auth)/login/page.tsx`, `apps/web/src/app/(auth)/signup/page.tsx`
  - Do: Create `middleware.ts` that: (1) creates a Supabase server client with cookie handlers on request+response, (2) calls `supabase.auth.getUser()` to refresh session, (3) redirects unauthenticated users from `/dashboard`, `/screener/*`, `/settings` to `/login`, (4) redirects authenticated users from `/login`, `/signup` to `/dashboard`. Export `config.matcher` excluding static files and `_next`. Create `auth/callback/route.ts` that exchanges the `code` query param for a session via `supabase.auth.exchangeCodeForSession(code)` and redirects to `/dashboard`. Create `(auth)/layout.tsx` with a centered card layout (no sidebar). Create `(auth)/login/page.tsx` as a `'use client'` component with email+password form calling `supabase.auth.signInWithPassword()`, error display, redirect to `/dashboard` on success, link to `/signup`. Create `(auth)/signup/page.tsx` as a `'use client'` component with email+password form calling `supabase.auth.signUp()`, shows "check your email" message on success, link to `/login`.
  - Verify: `npm run build` succeeds; visiting `/dashboard` while unauthenticated redirects to `/login`; login and signup forms render
  - Done when: Middleware protects routes, auth callback works, login/signup pages render with functional forms

- [ ] **T03: Build authenticated app shell with sidebar, placeholder pages, and API client** `est:45m`
  - Why: The app shell is what authenticated users see — sidebar navigation, placeholder pages for downstream slices, and the API client utility that S04-S06 consume for FastAPI calls.
  - Files: `apps/web/src/app/(app)/layout.tsx`, `apps/web/src/app/(app)/dashboard/page.tsx`, `apps/web/src/app/(app)/screener/puts/page.tsx`, `apps/web/src/app/(app)/screener/calls/page.tsx`, `apps/web/src/app/(app)/settings/page.tsx`, `apps/web/src/lib/api-client.ts`
  - Do: Create `(app)/layout.tsx` as the authenticated shell — server component that reads user via `supabase.auth.getUser()`, displays sidebar with nav links (Dashboard, Put Screener, Call Screener, Settings using `<Link>` with active state highlighting), top bar with user email, and a logout button (client component) that calls `supabase.auth.signOut()` and redirects to `/login`. Use Tailwind for layout (sidebar left, content right). Create placeholder pages: `dashboard/page.tsx` ("Dashboard — coming in S06"), `screener/puts/page.tsx` ("Put Screener — coming in S05"), `screener/calls/page.tsx` ("Call Screener — coming in S05"), `settings/page.tsx` ("Settings — coming in S04"). Create `lib/api-client.ts` with `apiFetch(path, options)` that: (1) gets the Supabase session via `createBrowserClient().auth.getSession()`, (2) injects `Authorization: Bearer <access_token>` header, (3) calls `fetch()` with the path (relative, proxied to FastAPI via next.config.ts rewrite). Handle missing session by redirecting to `/login`.
  - Verify: `npm run build` succeeds; authenticated user sees sidebar with all nav links; clicking nav links renders placeholder pages; logout redirects to `/login`; `apiFetch()` sends Bearer token (visible in browser devtools)
  - Done when: App shell renders with sidebar, all placeholder pages work, logout works, API client utility exists and injects auth headers

## Files Likely Touched

- `apps/web/package.json`
- `apps/web/next.config.ts`
- `apps/web/tsconfig.json`
- `apps/web/.env.local.example`
- `apps/web/src/lib/supabase/client.ts`
- `apps/web/src/lib/supabase/server.ts`
- `apps/web/src/lib/api-client.ts`
- `apps/web/src/middleware.ts`
- `apps/web/src/app/layout.tsx`
- `apps/web/src/app/page.tsx`
- `apps/web/src/app/auth/callback/route.ts`
- `apps/web/src/app/(auth)/layout.tsx`
- `apps/web/src/app/(auth)/login/page.tsx`
- `apps/web/src/app/(auth)/signup/page.tsx`
- `apps/web/src/app/(app)/layout.tsx`
- `apps/web/src/app/(app)/dashboard/page.tsx`
- `apps/web/src/app/(app)/screener/puts/page.tsx`
- `apps/web/src/app/(app)/screener/calls/page.tsx`
- `apps/web/src/app/(app)/settings/page.tsx`
