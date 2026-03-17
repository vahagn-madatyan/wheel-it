# GSD Knowledge

Recurring gotchas, non-obvious rules, and useful patterns discovered during execution.

---

### FastAPI HTTPBearer returns 401, not 403 (v0.135.1)

**Context:** T03 (S02/M004) — JWT auth middleware tests.

FastAPI >=0.109 changed `HTTPBearer()` auto_error from 403 to 401 for missing Authorization headers. The plan and Supabase docs may reference 403, but our pinned FastAPI 0.135.1 returns 401 with `{"detail": "Not authenticated"}`. Tests must assert 401 for missing auth header.

---

### create-next-app@latest installs Next.js 16, not 15

**Context:** T01 (S03/M004) — Next.js project scaffold.

As of March 2026, `npx create-next-app@latest` installs Next.js 16.1.7. Plans referencing "Next.js 15" should not be treated as a blocker — the App Router API, `cookies()` async behavior, and `@supabase/ssr` integration are identical. The only notable change is Next.js 16 uses Turbopack by default for builds.

---

### Next.js 16 deprecates middleware.ts in favor of "proxy"

**Context:** T02 (S03/M004) — Auth middleware.

Next.js 16.1.7 shows warning: "The 'middleware' file convention is deprecated. Please use 'proxy' instead." Despite the warning, `middleware.ts` compiles and runs correctly — route protection, cookie handlers, and redirects all work. The proxy convention is documented at `nextjs.org/docs/messages/middleware-to-proxy`. Migration is optional for now but should be considered in a future cleanup task.
