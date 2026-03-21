# Wheeely: Backend Fix + Frontend Overhaul

## Context

The app is broken in two ways: (1) the FastAPI backend can't verify Supabase JWTs because Supabase now issues ES256 tokens but the auth service was built for HS256 and a recent patch using `python-jose` for ES256 is causing 500s, and (2) the frontend is a bare-bones Tailwind prototype that needs a complete visual overhaul to match modern fintech apps like Robinhood/Webull.

---

## Part A: Fix Backend Auth (Internal Server Error)

### Root Cause

`python-jose` is effectively unmaintained and its `jwk.construct()` doesn't reliably handle EC/ES256 keys from JWKS. The current `auth.py` also has: (a) synchronous `urllib.request.urlopen` blocking the async event loop, (b) unhandled `ValueError` exceptions propagating as 500s, (c) zero ES256 test coverage.

### Plan

**A1. Swap `python-jose` for `PyJWT`** in `apps/api/requirements.txt`
- Remove: `python-jose[cryptography]>=3.3.0`
- Add: `PyJWT[crypto]>=2.8.0`
- PyJWT has a built-in `PyJWKClient` that handles JWKS fetching, EC key parsing, `kid` matching, and caching natively

**A2. Rewrite `apps/api/services/auth.py`**
- Use `PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600)` for ES256
- Keep HS256 fallback using `SUPABASE_JWT_SECRET`
- Catch-all `except Exception` after `ExpiredSignatureError` to prevent any unhandled 500
- Lazy-init the JWKS client from `SUPABASE_URL` env var

**A3. Update test imports** in `apps/api/tests/conftest.py` and `apps/api/tests/test_auth.py`
- Change `from jose import jwt` to `import jwt` (PyJWT)
- `jwt.encode()` / `jwt.decode()` API is nearly identical between the two libs
- Add ES256 test case using a generated EC key pair

**A4. Add startup validation** in `apps/api/main.py` lifespan
- Pre-warm JWKS cache during startup
- Log clear errors if `SUPABASE_URL` is missing

### Files to modify
- `apps/api/requirements.txt`
- `apps/api/services/auth.py` (full rewrite)
- `apps/api/tests/conftest.py` (import change)
- `apps/api/tests/test_auth.py` (import change + ES256 tests)
- `apps/api/main.py` (startup validation)
- `Dockerfile.api` (rebuild picks up new dep)

---

## Part B: Frontend Visual Overhaul (Robinhood/Webull Style)

### Design Direction

Dark-first fintech UI. Slate-blue-tinted dark backgrounds, green for gains, red for losses, purple accent for brand. Clean typography, card-based layouts, skeleton loaders, responsive with mobile bottom nav.

### B1. Add Dependencies

```
npm install lucide-react framer-motion recharts clsx tailwind-merge \
  @radix-ui/react-slot @radix-ui/react-dialog @radix-ui/react-select \
  @radix-ui/react-tooltip @radix-ui/react-dropdown-menu
```

### B2. Theme System (`globals.css` rewrite)

Replace the current 27-line CSS with a full design token system:

| Token | Value | Use |
|-------|-------|-----|
| `--background` | `#0C0D10` | App background |
| `--surface-0` | `#12131A` | Cards, sidebar |
| `--surface-1` | `#1A1B25` | Elevated cards, hover |
| `--surface-2` | `#232430` | Inputs, table headers |
| `--border` | `#2C2D3A` | Borders, dividers |
| `--text-primary` | `#F1F1F3` | Primary text |
| `--text-secondary` | `#9395A5` | Muted text |
| `--accent` | `#6C5CE7` | Buttons, active states |
| `--gain` | `#00D26A` | Profit, connected |
| `--loss` | `#FF4757` | Loss, errors |

Register all in `@theme inline` block for Tailwind v4 utility generation. Add `@custom-variant dark` for class-based dark mode. Add skeleton shimmer keyframe.

### B3. Create UI Primitives (`src/components/ui/`)

New reusable components (all use theme tokens, no hardcoded colors):
- `button.tsx` — variants: primary (purple), secondary, danger, ghost; loading state with Loader2 icon
- `card.tsx` — Card, CardHeader, CardTitle, CardContent
- `input.tsx` — dark-styled with label, error state, optional icon prefix
- `badge.tsx` — status badges (connected, paper/live, wheel states)
- `skeleton.tsx` — shimmer loading placeholders
- `data-table.tsx` — replaces `screener-results-table.tsx`; Lucide sort icons, right-aligned numerics, conditional coloring
- `alert.tsx`, `spinner.tsx`, `toggle.tsx`, `empty-state.tsx`, `page-header.tsx`
- `src/lib/cn.ts` — `clsx` + `tailwind-merge` utility

### B4. Layout Restructure

**`(app)/layout.tsx`** — decompose into:
- `layout/sidebar.tsx` — dark sidebar with Lucide icons, collapsible on desktop, overlay drawer on tablet, hidden on mobile
- `layout/header.tsx` — dark header with user dropdown
- `layout/mobile-nav.tsx` — bottom tab bar for mobile (`md:hidden`)
- `layout/logo.tsx` — Wheeely wordmark

**`(auth)/layout.tsx`** — glassmorphic centered card on dark background with subtle animated gradient orbs

### B5. Extract Shared Hooks

- `hooks/use-key-status.ts` — the key-status check logic duplicated in dashboard, put screener, and call screener
- `hooks/use-polling.ts` — the polling pattern duplicated between screeners

### B6. Rewrite All Pages

**Auth pages** (login, signup): dark inputs, purple CTA button, glassmorphic card, Lucide icons for errors/success

**Dashboard**:
- 4 stat cards with icons (Wallet, PieChart, DollarSign, Shield) in responsive grid
- Wheel state mini-cards with colored left borders (blue=put, green=shares, amber=call)
- Positions table using new `data-table.tsx`
- Skeleton loaders for all loading states
- Page entrance animation (framer-motion fade+slide)

**Put/Call Screeners**:
- Dark-styled form with icon-prefixed inputs
- Progress indicator replacing bare spinner
- Results in new `data-table.tsx` with green annualized return highlighting
- Extract form differences (multi-symbol vs single-symbol) from shared wrapper

**Settings**:
- Provider cards with green dot for connected, dark styling
- Custom toggle component replacing raw checkbox
- Radix Dialog for delete confirmation (replaces `window.confirm`)
- Password inputs with show/hide toggle

### B7. Animations (framer-motion)

- Page transitions: fade + 8px y-slide, 200ms
- Dashboard stat cards: stagger 50ms
- Table rows: stagger 20ms (first 10 rows)
- Sidebar: width transition on expand/collapse

### Files to modify/create
- `apps/web/package.json` (add deps)
- `apps/web/src/app/globals.css` (full rewrite)
- `apps/web/src/app/layout.tsx` (dark class, metadata)
- `apps/web/src/app/(app)/layout.tsx` (decompose)
- `apps/web/src/app/(auth)/layout.tsx` (glassmorphic)
- All 4 page files (dashboard, puts, calls, settings)
- Both auth pages (login, signup)
- `apps/web/src/components/` (new ui/ directory + refactored components)
- `apps/web/src/lib/cn.ts` (new)
- `apps/web/src/hooks/` (new, 2 hooks)

### Files that do NOT change
- `src/lib/api-client.ts`
- `src/lib/supabase/client.ts`
- `src/lib/supabase/server.ts`
- `src/middleware.ts`
- `src/app/auth/callback/route.ts`
- `next.config.ts`

---

## Implementation Order

1. **Part A first** (backend fix) — get auth working so we can test the frontend
2. **B1-B2** — deps + theme system
3. **B3** — UI primitives
4. **B4** — layout shell
5. **B5** — shared hooks
6. **B6** — pages (auth first, then dashboard, screeners, settings)
7. **B7** — polish animations

---

## Verification

1. `docker compose up --build` — both containers start without errors
2. Sign up / sign in — auth flow works end-to-end
3. Settings → store Alpaca keys → "Connected" badge shows
4. Dashboard → account summary + positions load
5. Put/Call screener → submit → poll → results table renders
6. `python -m pytest tests/ -q` — all existing tests pass
7. `python -m pytest apps/api/tests/ -q` — API tests pass with PyJWT
8. Responsive: test at 375px (mobile), 768px (tablet), 1440px (desktop)
