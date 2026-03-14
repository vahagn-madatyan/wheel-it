# Premium Data Expansion Plan

Two premium data services to replace free-tier approximations with institutional-grade data.

| Service | Cost | Role |
|---------|------|------|
| **FMP** (Financial Modeling Prep) | $99/mo | Fundamentals, screening, earnings — replaces Finnhub entirely |
| **ORATS** | $99/mo | Options analytics — IV rank, fair value, skew, greeks |

Total: $198/mo. Each is independently useful and gated on its own API key.

---

## FMP — Fundamentals & Screening ($99/mo)

Replaces Finnhub free tier. Eliminates the biggest bottleneck in the pipeline: per-symbol fundamentals calls at 1.1s/symbol.

### Current Finnhub problems being solved

1. **Rate limit** — 60 calls/min shared across profile + metrics + earnings = ~20 symbols/min through Stage 2
2. **Data quality** — metric key names undocumented (`METRIC_FALLBACK_CHAINS` hack), D/E normalization guesswork (D027), patchy coverage on smaller names (D028)
3. **No server-side filtering** — full universe fetched from Alpaca, then each symbol checked one-by-one against Finnhub (2-3 API calls per symbol)

### F1 — Server-Side Universe Screening (replaces Stage 1 + most of Stage 2)

Collapse hundreds of per-symbol API calls into a single server-side screener request.

- **Endpoint:** `GET /stock-screener`
- **Params:** `marketCapMoreThan`, `sector`, `exchange`, `volumeMoreThan`, `betaMoreThan`, `betaLessThan`, `priceMoreThan`, `priceLessThan`, `country`, `isActivelyTrading`, `limit`
- **Example:**
  ```
  GET /stock-screener?marketCapMoreThan=500000000&volumeMoreThan=500000&exchange=NYSE,NASDAQ&isActivelyTrading=true&limit=500
  ```
- **Returns per stock:** symbol, companyName, marketCap, sector, industry, beta, price, volume, exchange, country — all in one response
- **Replaces:**
  - `fetch_universe()` — Alpaca `get_all_assets()` calls (2 API calls)
  - `filter_market_cap()` — Finnhub `company_profile2` per symbol
  - `filter_sector()` — Finnhub `company_profile2` per symbol
  - Partial `filter_avg_volume()` and `filter_price()` — currently computed from 250 days of bar data
- **Impact:** Stage 1 + Stage 2 market cap/sector filters collapse from O(N) API calls to 1. Universe arrives pre-filtered.

### F2 — Clean Fundamentals (replaces Finnhub basic_financials)

SEC-sourced financial ratios with consistent formatting. No more fallback chain guessing.

- **Endpoint:** `GET /ratios-ttm/{symbol}` or bulk `GET /ratios-ttm/{symbol1,symbol2,...}`
- **Fields:** `debtEquityRatioTTM`, `netProfitMarginTTM`, `revenueGrowth` (QoQ), `returnOnEquityTTM`, `currentRatioTTM`
- **Replaces:**
  - `extract_metric(metrics, "debt_equity")` + `METRIC_FALLBACK_CHAINS["debt_equity"]` — FMP returns a single `debtEquityRatioTTM` as a ratio (not sometimes-percentage)
  - `extract_metric(metrics, "net_margin")` + fallback chain
  - `extract_metric(metrics, "sales_growth")` + fallback chain
  - D/E normalization heuristic (D027) — eliminated entirely, FMP uses consistent ratio format
- **Bonus fields worth adding:**
  - `returnOnEquityTTM` — ROE filter for quality screening
  - `currentRatioTTM` — balance sheet health
  - `freeCashFlowPerShareTTM` — cash generation quality
- **Impact:** Eliminates `METRIC_FALLBACK_CHAINS`, D/E normalization hack, and "No Finnhub data" neutral-pass workaround

### F3 — Earnings Calendar (replaces Finnhub earnings_calendar)

- **Endpoint:** `GET /earning_calendar?from={date}&to={date}`
- **Returns:** `symbol`, `date`, `time` (bmo/amc), `epsEstimated`, `epsActual`, `revenueEstimated`, `revenueActual`
- **Replaces:** `finnhub_client.earnings_calendar()` — currently called per-symbol at 1.1s each
- **Bonus:** FMP returns EPS estimates alongside dates, enabling earnings surprise tracking
- **Impact:** Combined with F1 screener, earnings data arrives in bulk rather than per-symbol

### F4 — Company Profile Enrichment

- **Endpoint:** `GET /profile/{symbol}` or bulk
- **Fields beyond current use:** `fullTimeEmployees`, `ipoDate`, `isEtf`, `isFund`, `isActivelyTrading`, `description`
- **Use:** `isEtf`/`isFund` flags for cleaner universe filtering (currently inferred), `ipoDate` to avoid recent IPOs with unstable options chains

### F5 — Historical Financials (future: backtesting)

- **Endpoint:** `GET /income-statement/{symbol}?period=quarter&limit=20`
- **Not needed for live screening** but enables backtesting fundamental filters against historical data
- **FMP historical data goes back 30+ years** for major stocks — useful if we ever build a backtest suite

---

## ORATS — Options Analytics ($99/mo)

**API budget:** 20,000 requests/month, 1,000/min. Typical `--top-n 20` run ≈ 25 requests. ~800 runs/month headroom.

### O1 — Real IV Rank

Replace `compute_hv_percentile()` proxy with ORATS `/ivrank` endpoint.

- **Endpoint:** `GET /datav2/ivrank?ticker=AAPL,MSFT,...`
- **Fields:** `ivRank1y`, `ivPct1y`, `ivRank1m`, `ivPct1m`, `iv` (current ATM IV)
- **Batch:** comma-delimited tickers in one call
- **Replaces:** `compute_hv_percentile()` in `screener/market_data.py`, `hv_percentile` field/filter/column
- **Why:** HV percentile measures realized movement; IV rank measures market-priced premium. They diverge most around events — IV rank is the correct signal for "is premium elevated right now."
- **Display:** Replace "HV%ile" column with "IV Rank" (1y) and optionally "IV" (current ATM IV %)
- **Filter:** `iv_rank_min` per preset replaces `hv_percentile_min`

### O2 — IV/HV Ratio (Premium Edge)

Add IV/HV ratio as a scoring factor or filter.

- **Endpoint:** `GET /datav2/cores?ticker=...&fields=ivHvXernRatio,ivHvXernRatio1y,ivHvXernRatioStdv1y`
- **Meaning:** Ratio > 1.0 = implied vol exceeds realized vol = premium is rich relative to actual movement. This is the core edge in premium selling.
- **Use:** New filter (`iv_hv_ratio_min: 1.0` default) or scoring weight. A stock can have high IV rank but IV < HV — that means premium isn't actually rich vs movement.
- **Display:** "IV/HV" column in results table

### O3 — Fair Value Edge Detection

Use ORATS model pricing to avoid selling underpriced options.

- **Endpoint:** `GET /datav2/strikes?ticker=...&dte=30,45&delta=.20,.35`
- **Fields:** `putValue` (ORATS fair value), `putBidPrice` (market bid), `smvVol`, `putMidIv`
- **Logic:** Only sell puts where `market_bid >= putValue` (or `market_bid >= putValue * 0.95` with tolerance)
- **Replaces:** Current nearest-ATM selection (D033) with edge-aware selection
- **Bonus:** Accurate per-strike `delta`, `gamma`, `theta`, `vega` — replaces missing Alpaca greeks (D039 workaround)
- **Impact:** Smarter contract selection in both put and call screeners. Fewer "greeks is None" situations.

### O4 — Graduated Earnings Handling

Replace binary earnings exclusion with move-size-aware filtering.

- **Endpoint:** `GET /datav2/cores?ticker=...&fields=impliedEarningsMove,absAvgErnMv,daysToNextErn,nextErn`
- **Fields:**
  - `impliedEarningsMove` — market-implied % move for next earnings
  - `absAvgErnMv` — average actual move over last 12 quarters
  - `daysToNextErn` — days until next earnings
- **Current behavior:** Binary exclude if `days_to_earnings <= N` (D030)
- **New behavior:** Scale exclusion window by implied move size:
  - Implied move > 6% → exclude within 21 days
  - Implied move 3-6% → exclude within 14 days
  - Implied move < 3% → exclude within 7 days
- **Post-earnings opportunity:** Stocks where IV just crushed after earnings are prime wheel entry points. Flag recently-reported stocks with IV drop > 20% as "post-earnings opportunity."
- **Display:** "Ern Move" column showing implied % move

### O5 — Replace Finnhub Earnings Calls (superseded by F3)

ORATS `/cores` includes `nextErn`, `daysToNextErn`, `lastErn` + 12 quarters of dates/moves.

- **Eliminates:** `finnhub_client.py` earnings calendar calls (one per symbol, rate-limited at ~1.1s each)
- **Benefit:** One fewer API dependency, faster pipeline (earnings data bundled into the `/cores` call already needed for P2/P4)
- **Migration:** Remove `run_stage_1b_earnings()` Finnhub path; consume earnings data from ORATS cores response

### O6 — Skew Awareness

Use put skew to weight screener toward names with expensive puts.

- **Endpoint:** `GET /datav2/cores?ticker=...&fields=slope,slopepctile,slopeavg1y,slopeStdv1y`
- **Meaning:** Steep slope = puts are relatively expensive vs calls. Good for put selling, less good for call selling.
- **Use:** Scoring weight — boost put screener scores for steep-skew names, boost call screener for flat-skew names
- **Display:** Optional "Skew" column

---

---

## Implementation Notes

### New client modules

- `screener/fmp_client.py` — wraps FMP API v3/v4. Handles screener, ratios, earnings, profile endpoints. Bulk-capable.
- `screener/orats_client.py` — wraps ORATS Data API v2. Rate-limited, retry-capable.
- Both follow the same pattern as existing `finnhub_client.py`.

### Config

- `FMP_API_KEY` env var (via `.env` + `secure_env_collect`)
- `ORATS_API_TOKEN` env var (via `.env` + `secure_env_collect`)
- Each service gated on its own key — graceful degradation when absent

### Pipeline integration (with both services)

| Stage | Current | With FMP | With FMP + ORATS |
|-------|---------|----------|------------------|
| Universe | Alpaca `get_all_assets()` (2 calls) | FMP `/stock-screener` (1 call, pre-filtered) | Same |
| Stage 1 (cheap filters) | Local: price, volume, RSI, SMA200, HV%ile from Alpaca bars | Local technicals still from bars; market cap + sector pre-filtered by FMP | IV rank from ORATS `/ivrank` replaces HV%ile |
| Stage 1b (earnings) | Finnhub `earnings_calendar` per symbol | FMP `/earning_calendar` bulk call | ORATS `/cores` `daysToNextErn` + `impliedEarningsMove` for graduated filter |
| Stage 2 (fundamentals) | Finnhub profile + metrics per symbol (1.1s each) | FMP `/ratios-ttm` bulk — D/E, margin, growth in one call | IV/HV ratio from ORATS `/cores` as additional filter |
| Stage 3 (options) | Alpaca option snapshots | Same | ORATS `/strikes` for fair value edge + accurate greeks |
| Scoring | `compute_composite_score()` | Same + ROE/current ratio factors | + IV/HV ratio weight + skew weight |

### Pipeline with FMP only (no ORATS)

Still a major improvement. The pipeline becomes:
1. FMP `/stock-screener` → pre-filtered universe with market cap, sector, volume, price
2. Alpaca bars for remaining technicals (RSI, SMA200, HV%ile as proxy)
3. FMP `/ratios-ttm` bulk → clean D/E, margin, growth (no fallback chains)
4. FMP `/earning_calendar` → bulk earnings exclusion
5. Alpaca options → contract selection (unchanged)
6. Score and rank

Eliminates Finnhub entirely. Screener runs in seconds instead of minutes.

### Request budget per run (--top-n 20)

**FMP:**

| Call | Count | Notes |
|------|-------|-------|
| `/stock-screener` | 1 | Returns pre-filtered universe |
| `/ratios-ttm` (top-N) | 1-4 | Bulk, ~5 symbols per call |
| `/earning_calendar` | 1 | Date-range bulk |
| **Total** | ~6 | FMP allows 300 calls/min on starter |

**ORATS:**

| Call | Count | Notes |
|------|-------|-------|
| `/ivrank` (Stage 1 survivors) | 1 | Batched tickers |
| `/cores` (top-N survivors) | 1 | Batched |
| `/strikes` (per symbol) | 20 | One per top-N symbol |
| **Total** | ~22 | Well within 20k/month budget |

### Backward compatibility

Three tiers based on which keys are present:

| Keys present | Behavior |
|---|---|
| Neither | Current behavior: Finnhub fundamentals, HV%ile proxy, Alpaca options |
| FMP only | FMP replaces Finnhub for fundamentals/earnings/screening. HV%ile proxy remains. Alpaca options unchanged |
| FMP + ORATS | Full premium pipeline. Finnhub eliminated. IV rank, fair value edge, graduated earnings, skew |
| ORATS only | ORATS replaces HV%ile and enhances options selection. Finnhub still used for fundamentals |

### Finnhub removal

Once FMP is integrated and verified:
1. `finnhub_client.py` becomes dead code
2. `METRIC_FALLBACK_CHAINS` eliminated
3. D/E normalization hack (D027) eliminated
4. `FINNHUB_API_KEY` no longer required
5. `finnhub-python` removed from dependencies

### Implementation order

1. **FMP first** — biggest single impact (speed + data quality + Finnhub elimination)
2. **ORATS second** — options-side improvements layer on top of FMP-cleaned pipeline
3. **Execution cleanup** — unify put/call paths, remove dead code
4. Each can be implemented and shipped independently

---

## Execution Cleanup — Unify Put & Call Paths

The strategy execution layer has accumulated inconsistencies between put selling and call selling. These should be cleaned up alongside (or before) the premium data work.

### Current state

**Put selling** uses the older `core/strategy.py` + `core/execution.py` path:
- `filter_options()` — delta, yield, OI filters. No spread filter.
- `score_options()` — custom formula: `(1 - |delta|) × (250 / (DTE + 5)) × (bid / strike)`
- `select_options()` — best per underlying, score minimum, sells multiple
- DTE range: 0–21 days (from `config/params.py`)
- Strike constraint: none (just affordability — `100 × price ≤ buying_power`)

**Call selling** uses the newer `screener/call_screener.py`:
- `screen_calls()` — OI, spread, delta filters. Spread filter present.
- Ranking: raw annualized return `(premium / cost_basis) × (365 / DTE) × 100`
- DTE range: 14–60 days (hardcoded in `call_screener.py`)
- Strike constraint: must be ≥ cost basis
- Returns recommendations; `run_strategy.py` takes `recommendations[0]` and sells

**Dead code:**
- `sell_calls()` in `core/execution.py` — imported but unused in `run_strategy.py`
- `from core.execution import sell_calls` — unused import in `run_strategy.py`

### Problems

1. **No spread filter on puts** — calls check bid/ask spread, puts don't. Wide spreads on puts mean poor fills and inflated apparent premium.
2. **Different scoring** — puts use a custom score formula, calls use annualized return. No principled reason for the difference.
3. **DTE mismatch** — puts 0–21 days, calls 14–60 days. A put with 0 DTE is expiring today; questionable whether that should be sold.
4. **Dead code** — `sell_calls()` in `execution.py` still exists and is imported, creating confusion about which path is live.
5. **No cost-basis-like floor on puts** — calls enforce `strike ≥ cost_basis` to avoid selling below entry. Puts have no analogous guard (e.g., avoid strikes well above current price where assignment means overpaying).

### Proposed changes

#### E1 — Add spread filter to put screening

Add a bid/ask spread check to `filter_options()` in `strategy.py`, matching the call screener's approach. Currently put options with 50%+ spreads can pass — these will fill poorly.

#### E2 — Unify scoring to annualized return

Replace the custom put scoring formula with the same annualized return metric used for calls:
- Puts: `(bid / strike) × (365 / DTE) × 100` — annualized return on capital at risk
- Calls: `(premium / cost_basis) × (365 / DTE) × 100` — annualized return on shares held

Both become "annualized premium yield on capital deployed." Easier to reason about, directly comparable.

The current put formula `(1 - |delta|) × (250 / (DTE + 5)) × (bid / strike)` blends probability weighting into the score. That's valid, but delta filtering already handles assignment probability — weighting it again double-counts.

#### E3 — Align DTE ranges

Standardize to a minimum DTE of 7 days for both puts and calls. Selling options expiring in 0–6 days has poor risk/reward — gamma risk spikes and premium is mostly gone. Pull DTE bounds from config rather than hardcoding in `call_screener.py`.

#### E4 — Remove dead `sell_calls()` code

- Delete `sell_calls()` from `core/execution.py`
- Remove unused `from core.execution import sell_calls` in `run_strategy.py`
- `screen_calls()` + `client.market_sell()` in `run_strategy.py` is the live path

#### E5 — Build `screen_puts()` to match `screen_calls()` pattern

Create `screener/put_screener.py` with a `screen_puts()` function mirroring `screen_calls()`:
- Returns `list[PutRecommendation]` sorted by annualized return
- Applies spread filter, OI filter, delta filter
- `run_strategy.py` consumes recommendations and sells — same pattern as calls
- Replaces the `filter_options()` → `score_options()` → `select_options()` chain in `execution.py`

This makes both sides of the wheel use the same architecture:
```
run_strategy.py
  ├── screen_calls() → [CallRecommendation] → sell best
  └── screen_puts()  → [PutRecommendation]  → sell best per symbol until buying power exhausted
```

#### E6 — ORATS/FMP integration points

Once E5 exists, the premium data improvements slot in cleanly:
- ORATS fair value check (O3) → filter step inside `screen_puts()` / `screen_calls()`
- ORATS accurate greeks (O3) → replace Alpaca snapshot greeks in both screeners
- ORATS skew (O6) → scoring weight in both screeners
- FMP cost basis enrichment (F2) → better cost basis for call strike floor

---

## GUI & Deployment — SaaS Platform

### Goal

Multi-tenant SaaS platform for the wheel strategy with:
1. Full web dashboard for screening, execution, and portfolio monitoring
2. LLM-powered analysis (trade reasoning, market context, risk commentary)
3. Multi-tenant with per-user Alpaca credentials and encrypted secret storage
4. Stripe billing with free and premium tiers
5. Deployed on a unified stack — no split-brain architecture

### Why not Cloudflare

The original Cloudflare plan (Pages + Workers + D1) had a fundamental problem: Python can't run in Workers. That forced a split architecture with the real backend elsewhere. Adding LLM inference (LangChain, LiteLLM), multi-tenant secret management, Stripe webhooks, and background job processing makes the split untenable. Too many moving parts across two platforms.

**The right move: pick one platform that runs Python natively and handles everything.**

### Architecture — Render + Supabase

All services on Render. Supabase for auth, database, and encrypted secret storage.
Next.js calls FastAPI over Render's private network — zero public internet hops, no CORS.

```
┌──────────────────────────────────────────────────────────────────┐
│                          Render                                   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Web Service 1: Next.js (App Router, SSR)                  │  │
│  │  ├── Dashboard, Screener, Execution UI                     │  │
│  │  ├── Server Actions → FastAPI via private network          │  │
│  │  ├── Stripe checkout + portal redirects                    │  │
│  │  └── Supabase Auth (SSR client)                            │  │
│  └────────────────────────┬───────────────────────────────────┘  │
│                           │  Private network (10.x.x.x)          │
│  ┌────────────────────────▼───────────────────────────────────┐  │
│  │  Web Service 2: FastAPI + Uvicorn                          │  │
│  │  ├── /api/screen/*   — screening endpoints                 │  │
│  │  ├── /api/execute/*  — trade execution                     │  │
│  │  ├── /api/llm/*      — LLM analysis agents                │  │
│  │  ├── /api/keys/*     — Vault key management                │  │
│  │  ├── /api/stripe/*   — ALL Stripe webhooks (single target) │  │
│  │  ├── Alpaca SDK, ORATS, FMP clients                        │  │
│  │  ├── LangChain + LiteLLM                                   │  │
│  │  └── Per-user rate limiting (Redis counters)               │  │
│  └──────────────┬─────────────────────────────────────────────┘  │
│                 │                                                 │
│  ┌──────────────▼─────────────────────────────────────────────┐  │
│  │  Background Worker 1: Celery (screening + execution queue) │  │
│  │  ├── Screening pipeline (FMP → ORATS → Alpaca)             │  │
│  │  ├── Trade execution tasks                                 │  │
│  │  ├── CELERY_TASK_TIME_LIMIT = 120                          │  │
│  │  └── CELERY_TASK_ACKS_LATE = True (retry on crash)         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Background Worker 2: Celery (llm queue)                   │  │
│  │  ├── Screening analysis                                    │  │
│  │  ├── Trade reasoning generation                            │  │
│  │  ├── Risk metric computation                               │  │
│  │  └── Market context briefs                                 │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Redis (Render managed)                                    │  │
│  │  ├── Celery broker + result backend                        │  │
│  │  ├── FMP/ORATS response cache (TTLs below)                 │  │
│  │  │   ├── FMP /stock-screener: 15 min                       │  │
│  │  │   ├── FMP /ratios-ttm: 24 hours                         │  │
│  │  │   ├── ORATS /ivrank: 1 hour                             │  │
│  │  │   ├── ORATS /cores: 1 hour                              │  │
│  │  │   └── ORATS /strikes: 5 min                             │  │
│  │  ├── LLM response cache                                    │  │
│  │  │   ├── Screening analysis: 1 hour                        │  │
│  │  │   ├── Market context: 4 hours                           │  │
│  │  │   └── Risk metrics: 30 min                              │  │
│  │  └── Per-user rate limiting counters                       │  │
│  │      ├── Screening runs: 60/hour (premium), 3/day (free)   │  │
│  │      ├── Trade execution: 10/min                           │  │
│  │      └── LLM calls: 30/hour                                │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Cron Jobs (Render-native, no Celery Beat needed)          │  │
│  │  ├── Morning market brief: 8:30 AM ET weekdays             │  │
│  │  ├── Position sync: every 30 min during market hours       │  │
│  │  ├── Stale API key check: daily 6 AM ET                    │  │
│  │  └── FMP/ORATS cache warm: 9:00 AM ET weekdays             │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
         │
         │  Postgres connection (pooled via Supavisor)
         ▼
┌──────────────────────────────────────────────────────────────────┐
│                       Supabase                                    │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  Auth         │  │  Postgres    │  │  Vault                 │ │
│  │  ├── Email    │  │  ├── users   │  │  ├── Alpaca keys       │ │
│  │  ├── Google   │  │  ├── trades  │  │  ├── FMP keys          │ │
│  │  ├── GitHub   │  │  ├── runs    │  │  └── ORATS keys        │ │
│  │  └── JWT      │  │  ├── configs │  │                        │ │
│  │               │  │  └── RLS     │  │  Vault + app-layer     │ │
│  │               │  │              │  │  envelope encryption   │ │
│  └──────────────┘  └──────────────┘  └────────────────────────┘ │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  Stripe Sync (webhook → FastAPI → Postgres)                  ││
│  │  ├── subscription status                                     ││
│  │  ├── tier (free/premium)                                     ││
│  │  └── usage metering                                          ││
│  └──────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

#### Why this stack

| Concern | Solution | Why |
|---------|----------|-----|
| Frontend + SSR | **Render Web Service (Next.js)** | Server Actions call FastAPI over private network — no public hop, no CORS. SSR for SEO on marketing pages. |
| Python backend | **Render Web Service (FastAPI)** | Native Python, git push deploy, persistent containers. Private network access from Next.js. $7/mo Starter. |
| LLM inference | **Render Background Worker** | Dedicated Celery queue for LLM tasks. LangChain + LiteLLM call external APIs (OpenAI, Anthropic). Isolated from screening jobs — one can't block the other. |
| Database | **Supabase Postgres** | Row-Level Security for multi-tenant isolation. Managed Postgres, connection pooling via Supavisor, real-time subscriptions for live updates. Free tier: 500MB, 50k MAU. |
| Auth | **Supabase Auth** | Email, Google, GitHub login. JWT-based. RLS policies use `auth.uid()` — no auth middleware to write. |
| Secret storage | **Supabase Vault + envelope encryption** | Per-user API keys encrypted at rest via `pgsodium`, plus application-layer envelope encryption (per-user derived key). Even Supabase service role access alone can't decrypt raw keys. |
| Billing | **Stripe → FastAPI (single webhook target)** | All Stripe webhooks route to FastAPI. No dual-path race conditions. Checkout, customer portal, idempotent event processing. |
| Background jobs | **Celery + Redis on Render** | Two workers with separate queues: `screening+execution` and `llm`. Task timeouts, ack-late retries, dead letter queue. |
| Caching | **Redis on Render** | FMP/ORATS response cache with TTLs, LLM response cache, per-user rate limit counters. Prevents blowing through API budgets at scale. |
| Scheduling | **Render Cron Jobs** | Native cron — no Celery Beat. Morning briefs, position syncs, cache warming. |
| Platform unity | **Everything on Render** | One dashboard, one billing, one deploy pipeline. Private networking between all services. Preview environments for PRs. |

#### Why not Convex

Convex is excellent for real-time apps but wrong for this project:
- **No Python** — Convex functions run in JS/TS. Our entire trading engine is Python. We'd need a separate Python backend anyway, recreating the Cloudflare split-brain problem.
- **No raw SQL** — Convex uses a document model. Trade history, screening runs, and financial data are deeply relational (joins, aggregations, time-range queries).
- **Vendor lock-in** — Supabase is open-source Postgres. If we outgrow Supabase hosted, we migrate to self-hosted Postgres. Convex has no self-hosted option.

#### Why not Vercel + Railway

Splitting frontend (Vercel) and backend (Railway) across two platforms creates:
- **Cross-platform latency** — Next.js Server Actions must call the Python API over the public internet instead of a private network.
- **CORS configuration** — public API requires CORS headers and additional auth checks.
- **Two billing dashboards** — two platforms to monitor, two deploy pipelines to maintain.
- **Coordinated deploys** — breaking API changes require syncing deploys across platforms.

Render eliminates all of this. One platform, private networking, unified deploys.

### Database — Supabase Postgres

#### Schema

```sql
-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ================================================================
-- USERS & AUTH
-- ================================================================

-- Profile data (extends Supabase auth.users)
CREATE TABLE public.profiles (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name    TEXT,
    avatar_url      TEXT,
    stripe_customer_id TEXT UNIQUE,
    tier            TEXT NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'premium')),
    subscription_status TEXT DEFAULT 'inactive',  -- 'active' | 'past_due' | 'cancelled' | 'inactive'
    subscription_id TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.profiles (id, display_name)
    VALUES (NEW.id, NEW.raw_user_meta_data->>'full_name');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ================================================================
-- USER API KEYS (encrypted via Supabase Vault)
-- ================================================================

-- Stores references to Vault secrets, not raw keys
CREATE TABLE public.user_api_keys (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider        TEXT NOT NULL CHECK (provider IN ('alpaca', 'fmp', 'orats')),
    vault_secret_id UUID NOT NULL,              -- reference to vault.secrets
    is_paper        BOOLEAN DEFAULT TRUE,       -- for Alpaca: paper vs live
    label           TEXT,                        -- user-friendly label
    verified_at     TIMESTAMPTZ,                -- last successful API call
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, provider)
);

-- ================================================================
-- SCREENING
-- ================================================================

-- Saved screener configurations
CREATE TABLE public.screener_configs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    preset          TEXT NOT NULL DEFAULT 'moderate',
    overrides       JSONB NOT NULL DEFAULT '{}',
    is_default      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Watchlists
CREATE TABLE public.watchlists (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name            TEXT NOT NULL DEFAULT 'default',
    symbols         JSONB NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Screening run history
CREATE TABLE public.screening_runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    config_id       UUID REFERENCES public.screener_configs(id),
    run_type        TEXT NOT NULL CHECK (run_type IN ('put_screen', 'call_screen', 'full_pipeline')),
    status          TEXT NOT NULL DEFAULT 'queued'
                    CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    symbol_count    INTEGER,
    pass_count      INTEGER,
    error           TEXT,
    -- LLM analysis
    llm_analysis    JSONB,                      -- AI-generated summary + reasoning
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Normalized screening results (one row per result, queryable)
CREATE TABLE public.screening_results (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id          UUID NOT NULL REFERENCES public.screening_runs(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    symbol          TEXT NOT NULL,
    underlying      TEXT NOT NULL,
    score           NUMERIC,
    annualized_return NUMERIC,
    strike          NUMERIC,
    expiration      DATE,
    delta           NUMERIC,
    iv_rank         NUMERIC,
    premium         NUMERIC,
    metadata        JSONB DEFAULT '{}',          -- additional per-result data (greeks, fundamentals)
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ================================================================
-- TRADES & POSITIONS
-- ================================================================

-- Trade execution log
CREATE TABLE public.trades (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    screening_run_id UUID REFERENCES public.screening_runs(id),
    symbol          TEXT NOT NULL,
    underlying      TEXT NOT NULL,
    side            TEXT NOT NULL CHECK (side IN ('sell_put', 'sell_call')),
    strike          NUMERIC NOT NULL,
    expiration      DATE NOT NULL,
    premium         NUMERIC,
    delta           NUMERIC,
    annualized_return NUMERIC,
    order_id        TEXT,                       -- Alpaca order ID
    order_status    TEXT CHECK (order_status IN ('pending', 'filled', 'partially_filled',
                                                  'cancelled', 'rejected', 'expired')),
    filled_price    NUMERIC,
    filled_qty      INTEGER,
    notes           TEXT,
    -- LLM reasoning
    llm_reasoning   TEXT,                       -- AI explanation for why this trade
    executed_at     TIMESTAMPTZ DEFAULT now(),
    -- Soft delete (never hard-delete trade records — audit trail)
    archived_at     TIMESTAMPTZ                  -- NULL = active, set = hidden from UI but preserved
);

-- Wheel state snapshots
CREATE TABLE public.wheel_positions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    underlying      TEXT NOT NULL,
    state           TEXT NOT NULL CHECK (state IN ('short_put', 'long_shares', 'short_call')),
    entry_price     NUMERIC,
    qty             INTEGER,
    option_symbol   TEXT,
    cost_basis      NUMERIC,                    -- for covered call strike floor
    total_premium   NUMERIC DEFAULT 0,          -- accumulated premium collected
    cycles          INTEGER DEFAULT 0,          -- how many wheel cycles completed
    updated_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, underlying)
);

-- ================================================================
-- BILLING
-- ================================================================

-- Stripe webhook event log (idempotency)
CREATE TABLE public.stripe_events (
    id              TEXT PRIMARY KEY,            -- Stripe event ID
    type            TEXT NOT NULL,
    processed_at    TIMESTAMPTZ DEFAULT now(),
    payload         JSONB
);

-- Usage tracking for metered billing (future)
CREATE TABLE public.usage_records (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,               -- 'screening_run' | 'llm_analysis' | 'trade_execution'
    tier_required   TEXT NOT NULL DEFAULT 'free', -- which tier was needed
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ================================================================
-- ROW LEVEL SECURITY
-- ================================================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.screener_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.watchlists ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.screening_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.screening_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wheel_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_records ENABLE ROW LEVEL SECURITY;

-- Users can only see/modify their own data
CREATE POLICY "Users own their profile"
    ON public.profiles FOR ALL USING (auth.uid() = id);

CREATE POLICY "Users own their API keys"
    ON public.user_api_keys FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users own their configs"
    ON public.screener_configs FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users own their watchlists"
    ON public.watchlists FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users own their screening runs"
    ON public.screening_runs FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users own their screening results"
    ON public.screening_results FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users own their trades"
    ON public.trades FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users own their positions"
    ON public.wheel_positions FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users own their usage"
    ON public.usage_records FOR ALL USING (auth.uid() = user_id);

-- ================================================================
-- INDEXES
-- ================================================================

CREATE INDEX idx_trades_user_date ON public.trades (user_id, executed_at DESC);
CREATE INDEX idx_trades_user_underlying ON public.trades (user_id, underlying);  -- cost basis lookups
CREATE INDEX idx_screening_runs_user ON public.screening_runs (user_id, created_at DESC);
CREATE INDEX idx_screening_results_run ON public.screening_results (run_id);
CREATE INDEX idx_screening_results_user_symbol ON public.screening_results (user_id, symbol);
CREATE INDEX idx_wheel_positions_user ON public.wheel_positions (user_id, underlying);
CREATE INDEX idx_usage_user_date ON public.usage_records (user_id, created_at DESC);
```

### Secret Management — Supabase Vault + Envelope Encryption

User API keys (Alpaca key/secret, FMP, ORATS) use a two-layer encryption model.
Supabase Vault alone relies on the service role key — if the FastAPI container is compromised, all user keys are exposed. Envelope encryption adds a per-user derived key so service role access alone isn't sufficient.

#### Layer 1: Application-layer envelope encryption

Before storing in Vault, encrypt the raw key with a per-user derived key:

```python
import hashlib
from cryptography.fernet import Fernet
import base64

def derive_user_key(user_id: str, app_secret: str) -> bytes:
    """Derive a per-user encryption key from user ID + app secret.
    app_secret is stored in Render env vars, NOT in Supabase."""
    dk = hashlib.pbkdf2_hmac('sha256', app_secret.encode(), user_id.encode(), 100_000)
    return base64.urlsafe_b64encode(dk)

def encrypt_for_user(user_id: str, app_secret: str, plaintext: str) -> str:
    key = derive_user_key(user_id, app_secret)
    return Fernet(key).encrypt(plaintext.encode()).decode()

def decrypt_for_user(user_id: str, app_secret: str, ciphertext: str) -> str:
    key = derive_user_key(user_id, app_secret)
    return Fernet(key).decrypt(ciphertext.encode()).decode()
```

#### Layer 2: Supabase Vault encryption at rest

```sql
-- Store: envelope-encrypted ciphertext goes into Vault (not raw key)
SELECT vault.create_secret(
    'gAAAAABk...<envelope_encrypted>',  -- already encrypted by app layer
    'alpaca_api_key',                    -- name
    'User xyz Alpaca API key'            -- description
);
-- Returns a secret UUID → stored in user_api_keys.vault_secret_id

-- Retrieve at runtime (only from server-side, never from client)
SELECT decrypted_secret
FROM vault.decrypted_secrets
WHERE id = '<vault_secret_id>';
-- Returns envelope-encrypted ciphertext, NOT the raw key
-- App must then call decrypt_for_user() to get the actual key
```

#### Security model

- **Two keys required to decrypt:** Supabase service role (Vault layer) + APP_ENCRYPTION_SECRET (Render env var, app layer). Compromising either one alone is insufficient.
- Raw keys are never stored in application tables — only Vault references (UUIDs)
- Vault uses `pgsodium` for encryption at rest
- Decryption happens server-side only — the Python backend reads envelope-encrypted ciphertext via Supabase service role, then decrypts with the per-user derived key
- RLS ensures users can only see their own `user_api_keys` rows (but can't decrypt — that requires service role + app secret)
- Keys are decrypted only for the duration of an API call, then discarded from memory
- **Audit trail:** Every Vault read is logged to `vault_access_log` table with user_id, provider, timestamp, and calling endpoint
- **Rotation:** APP_ENCRYPTION_SECRET can be rotated by re-encrypting all Vault entries in a background migration

#### Vault access logging

```sql
CREATE TABLE public.vault_access_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id),
    provider        TEXT NOT NULL,
    endpoint        TEXT NOT NULL,    -- which API endpoint triggered the read
    accessed_at     TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_vault_access_user ON public.vault_access_log (user_id, accessed_at DESC);
```

### LLM Integration — LangChain + LiteLLM

#### LiteLLM — Model Router

LiteLLM provides a unified interface to 100+ LLM providers. We use it as the model layer so users on premium tier can pick their preferred model, and we can switch providers without code changes.

```python
# config
LITELLM_MODELS = {
    "fast": "gpt-4o-mini",           # screening summaries, quick analysis
    "reasoning": "claude-sonnet-4-20250514",  # trade reasoning, risk analysis
    "cheap": "gpt-3.5-turbo",        # free-tier users, simple summaries
}
```

#### LangChain — Agent Pipelines

LangChain orchestrates multi-step LLM workflows:

**1. Screening Analysis Agent**
- Input: screening results (passing stocks, filter scores, IV rank, fundamentals)
- Output: natural-language summary of why each stock passed/failed, sector concentration risk, overall market context
- Tier: premium only

**2. Trade Reasoning Agent**
- Input: selected contract details (strike, DTE, delta, premium, IV rank, IV/HV ratio)
- Output: structured reasoning for the trade — why this strike, why this DTE, risk factors, expected outcome
- Stored in `trades.llm_reasoning` for trade journal
- Tier: premium only

**3. Portfolio Risk Metrics Agent**
- Input: current wheel positions, account exposure, sector breakdown
- Output: risk metrics report — concentration %, sector correlation, max drawdown scenario, buying power utilization
- Reports numbers and facts only. Does NOT recommend position sizes or suggest trades. Users interpret the metrics and decide.
- Example output: "3 of 5 positions are in tech (60% concentration). Portfolio delta is -1.8. If SPY drops 5%, estimated loss is $X based on current positions."
- Runs on demand from dashboard
- Tier: premium only

**4. Market Context Agent**
- Input: watchlist symbols, recent price action, earnings calendar, IV rank data
- Output: "market brief" — which watchlist stocks have notable activity today (IV rank spikes, unusual volume, earnings proximity, news events)
- Reports facts and data points. Does NOT say stocks "look interesting" or are "good opportunities." Uses language like "notable activity," "elevated IV rank," "approaching earnings."
- Can run on schedule (morning brief) via Render cron job
- Tier: premium only (free tier gets basic screening without AI commentary)

**Regulatory language rules for ALL agents:**
- Never use: "recommend," "suggest," "you should," "best option," "opportunity"
- Always use: "data shows," "metrics indicate," "notable activity," "based on your filters"
- Every LLM response includes footer: "AI-generated analysis for informational purposes only. Not investment advice."
- Agent system prompts explicitly instruct the model to report data, not recommend actions

#### Caching

LLM responses cached in Redis with TTL:
- Screening analysis: 1 hour (results don't change until re-screened)
- Market context: 4 hours (refreshed a few times per trading day)
- Trade reasoning: permanent (stored in DB, not re-generated)
- Risk metrics: 30 minutes (positions can change)

### Stripe Billing

#### Tiers

| Feature | Free | Premium ($29/mo) |
|---------|------|-------------------|
| Put screener | ✅ 3 runs/day | ✅ Unlimited |
| Call screener | ✅ 3 runs/day | ✅ Unlimited |
| Execute trades | ✅ Paper only | ✅ Paper + Live |
| Watchlists | 1 (10 symbols) | Unlimited |
| Screener presets | Default only | Custom presets |
| LLM analysis | ❌ | ✅ All agents |
| Screening history | 7 days | Unlimited |
| Trade journal | ❌ | ✅ With AI reasoning |
| ORATS data | ❌ (HV proxy) | ✅ Real IV rank, fair value |
| FMP data | ❌ (Finnhub) | ✅ Server-side screening |

#### Implementation

```
Stripe Checkout → creates subscription → webhook → Supabase
                                                      │
                                                      ▼
                                              profiles.tier = 'premium'
                                              profiles.subscription_status = 'active'
                                              profiles.subscription_id = 'sub_xxx'
```

- **Checkout:** Next.js server action creates Stripe checkout session, redirects user
- **Webhooks:** `POST /api/stripe/webhook` on FastAPI ONLY (single webhook target — no dual-path race conditions)
  - `checkout.session.completed` → set tier to premium
  - `invoice.payment_succeeded` → confirm active
  - `invoice.payment_failed` → set status to past_due
  - `customer.subscription.deleted` → downgrade to free
- **Enforcement:** FastAPI middleware checks `profiles.tier` before allowing premium features. Degradation is graceful — premium features just disappear from the UI, existing data remains accessible.
- **Customer portal:** Stripe-hosted portal for billing management (cancel, update payment, view invoices)
- **Idempotency:** `stripe_events` table deduplicates webhook replays

### Python Backend — FastAPI on Render

#### Endpoints (expanded from original)

```
Auth
──────────────────────────────────────────────────
POST   /api/auth/verify          Verify Supabase JWT, return user context + tier

Screener
──────────────────────────────────────────────────
POST   /api/screen/puts          Run put screener (async → returns run_id)
POST   /api/screen/calls         Run call screener (async → returns run_id)
GET    /api/screen/runs/{id}     Poll screening run status + results
GET    /api/screen/presets       List available presets
POST   /api/screen/full          Run full pipeline (async)
WS     /api/screen/ws/{run_id}   WebSocket for live screening progress

Strategy Execution
──────────────────────────────────────────────────
GET    /api/positions            Current positions + wheel state (from user's Alpaca)
POST   /api/execute/sell-puts    Sell selected put contracts (requires confirmation token)
POST   /api/execute/sell-calls   Sell selected call contracts (requires confirmation token)
GET    /api/account              Account info, buying power, risk

LLM Agents
──────────────────────────────────────────────────
POST   /api/llm/analyze-screen   Analyze screening results (premium)
POST   /api/llm/trade-reason     Generate trade reasoning (premium)
POST   /api/llm/risk-assess      Portfolio risk assessment (premium)
POST   /api/llm/market-brief     Daily market context (premium)

User Config
──────────────────────────────────────────────────
GET    /api/keys/status          API key connection status (no values)
POST   /api/keys/{provider}      Store API key in Vault
DELETE /api/keys/{provider}      Remove API key from Vault
POST   /api/keys/{provider}/verify  Test API key validity

Billing
──────────────────────────────────────────────────
POST   /api/stripe/checkout      Create checkout session
POST   /api/stripe/portal        Create customer portal session
POST   /api/stripe/webhook       Handle Stripe webhooks

Market Data
──────────────────────────────────────────────────
GET    /api/quotes/{symbol}      Latest quote
GET    /api/chain/{symbol}       Option chain with greeks
```

#### Key design decisions (updated)

- **No auto-execute** — GUI shows screener matches, user selects and confirms. Execution endpoints require a confirmation token (generated client-side after user reviews the order summary).
- **Per-user Alpaca credentials** — every Alpaca API call uses the requesting user's keys, decrypted from Vault (envelope + pgsodium) for the duration of the call. No shared brokerage account. Consider Alpaca OAuth as primary auth path (scoped permissions, revocable) with raw API keys as fallback.
- **Tier enforcement in middleware** — FastAPI dependency checks `user.tier` before premium endpoints. Returns 403 with upgrade prompt.
- **Screening is async** — Celery task on `screening` queue, results stored in `screening_runs` + `screening_results`. Client polls or connects via WebSocket.
- **LLM calls are async** — Celery tasks on `llm` queue with Redis caching. Results stored in DB for re-display. Isolated from screening — separate worker.
- **Stateless backend** — all persistent state in Supabase Postgres. Redis for ephemeral state only. Render services can be restarted/scaled freely.
- **Per-user rate limiting** — Redis sliding window counters. Screening: 60/hour premium, 3/day free. Execution: 10/min. LLM: 30/hour. Prevents single user from burning API budgets.

### Frontend — Next.js on Render

#### Pages / Views (expanded)

**Landing / Marketing**
- Hero, features, pricing table, CTA → signup
- SSR for SEO

**Dashboard (authenticated home)**
- Current wheel state: position table (short_put → long_shares → short_call), P&L, days held
- Account summary: buying power, total risk, available capital
- AI market brief (premium): today's opportunities from watchlist
- Quick actions: "Run Put Screener", "Run Call Screener"

**Put Screener**
- Filter controls: preset selector, delta range sliders, DTE range, min OI, max spread, yield range, market cap range, sector checkboxes
- "Run Screen" → progress bar → results table
- Results table: sortable, filterable, checkboxes for selection
- AI analysis panel (premium): why each stock scored well/poorly
- Selected contracts panel → total capital at risk → "Execute" with confirmation modal

**Call Screener**
- Symbol selector (from `long_shares` positions)
- Cost basis auto-populated from position data
- Same filter controls, results table, AI analysis
- Single-select per underlying → execute with confirmation

**Watchlist Manager**
- Add/remove symbols, drag reorder
- Import from screener results
- Per-symbol mini-card: price, IV rank, sector, last screened
- "Screen All" button

**Trade Journal (premium)**
- Every trade with AI reasoning
- P&L per trade, per symbol, aggregate
- Charts: cumulative premium, win rate, avg DTE, avg delta
- Export to CSV

**Settings**
- API keys: connect Alpaca (paper/live toggle), FMP, ORATS — status indicators
- Screener presets: create/edit/delete
- Risk limits: max risk per position, max total risk, max positions
- Notification preferences (future: email/SMS on assignment, expiry)

**Billing**
- Current tier, usage stats
- Upgrade/downgrade button → Stripe checkout/portal
- Invoice history

#### Tech Stack

- **Next.js 15** (App Router, Server Actions for Stripe checkout + auth flows)
- **Tailwind CSS + shadcn/ui** — component library
- **TanStack Table** — sortable/filterable results
- **TanStack Query** — server state, polling, WebSocket integration
- **Recharts** — P&L charts, IV visualization
- **Zustand** — local UI state
- **Supabase JS client** — auth, real-time subscriptions
- **Private network API client** — `api.ts` calls FastAPI via Render internal URL (`http://wheely-api:8000`), never public internet

### Deployment Architecture

```
wheeely/
├── apps/
│   ├── web/                      # Next.js app → Render Web Service
│   │   ├── app/
│   │   │   ├── (marketing)/      # Landing, pricing (SSR)
│   │   │   ├── (app)/            # Authenticated app shell
│   │   │   │   ├── dashboard/
│   │   │   │   ├── screener/
│   │   │   │   │   ├── puts/
│   │   │   │   │   └── calls/
│   │   │   │   ├── watchlist/
│   │   │   │   ├── journal/
│   │   │   │   ├── settings/
│   │   │   │   └── billing/
│   │   │   └── api/
│   │   │       └── stripe/
│   │   │           └── checkout/route.ts  # Creates session, redirects only
│   │   ├── components/
│   │   │   ├── ui/               # shadcn
│   │   │   ├── screener/
│   │   │   ├── dashboard/
│   │   │   ├── execution/
│   │   │   └── billing/
│   │   └── lib/
│   │       ├── api.ts            # FastAPI client (private network URL)
│   │       ├── supabase/         # Auth + DB client
│   │       └── stripe.ts         # Stripe checkout helpers only
│   │
│   └── api/                      # FastAPI app → Render Web Service
│       ├── main.py               # FastAPI entry point
│       ├── auth/                 # Supabase JWT verification
│       ├── billing/              # Stripe webhooks + subscription mgmt
│       ├── llm/                  # LangChain agents, LiteLLM config
│       ├── routers/              # API route modules
│       ├── vault/                # Supabase Vault + envelope encryption
│       ├── tasks/                # Celery task definitions
│       │   ├── screening.py      # screening + execution queue tasks
│       │   └── llm.py            # llm queue tasks
│       ├── cache/                # Redis caching layer (FMP/ORATS TTLs)
│       ├── ratelimit/            # Per-user rate limiting middleware
│       ├── screener/             # Existing screener code (moved)
│       ├── core/                 # Existing strategy code (moved)
│       └── celery_app.py         # Celery config: 3 queues (screening, execution, llm)
│
├── packages/
│   └── shared/                   # Shared types, constants
│       ├── types.ts              # TypeScript types
│       └── types.py              # Pydantic models (mirrored)
│
├── supabase/
│   ├── migrations/               # SQL migrations
│   │   ├── 00001_initial.sql
│   │   └── ...
│   └── config.toml               # Supabase project config
│
├── render.yaml                   # Render Blueprint — all services as code
├── docker-compose.yml            # Local dev: Postgres, Redis, API, Worker
└── turbo.json                    # Monorepo build config (Turborepo)
```

**render.yaml (Render Blueprint — infrastructure as code):**

```yaml
services:
  # --- Next.js Frontend ---
  - type: web
    name: wheely-web
    runtime: node
    repo: https://github.com/your-org/wheely
    rootDir: apps/web
    buildCommand: npm run build
    startCommand: npm run start
    plan: starter         # $7/mo
    envVars:
      - key: NEXT_PUBLIC_SUPABASE_URL
        sync: false
      - key: NEXT_PUBLIC_SUPABASE_ANON_KEY
        sync: false
      - key: API_BASE_URL
        fromService:
          name: wheely-api
          type: web
          property: hostport    # private network address
      - key: NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
        sync: false

  # --- FastAPI Backend ---
  - type: web
    name: wheely-api
    runtime: python
    repo: https://github.com/your-org/wheely
    rootDir: apps/api
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port 8000
    plan: starter         # $7/mo
    envVars:
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_SERVICE_ROLE_KEY
        sync: false
      - key: APP_ENCRYPTION_SECRET
        sync: false       # for envelope encryption
      - key: STRIPE_SECRET_KEY
        sync: false
      - key: STRIPE_WEBHOOK_SECRET
        sync: false
      - key: REDIS_URL
        fromService:
          name: wheely-redis
          type: redis
          property: connectionString
      - key: FMP_API_KEY
        sync: false
      - key: ORATS_API_TOKEN
        sync: false
      - key: LITELLM_API_KEY
        sync: false

  # --- Celery Worker 1: Screening + Execution ---
  - type: worker
    name: wheely-worker-screening
    runtime: python
    repo: https://github.com/your-org/wheely
    rootDir: apps/api
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A celery_app worker -Q screening,execution --concurrency=2
    plan: starter         # $7/mo
    envVars:
      - key: REDIS_URL
        fromService:
          name: wheely-redis
          type: redis
          property: connectionString
      # ... same Supabase + API keys as wheely-api

  # --- Celery Worker 2: LLM ---
  - type: worker
    name: wheely-worker-llm
    runtime: python
    repo: https://github.com/your-org/wheely
    rootDir: apps/api
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A celery_app worker -Q llm --concurrency=4
    plan: starter         # $7/mo
    envVars:
      - key: REDIS_URL
        fromService:
          name: wheely-redis
          type: redis
          property: connectionString
      # ... same LiteLLM + Supabase keys

  # --- Redis ---
  - type: redis
    name: wheely-redis
    plan: starter         # $10/mo
    maxmemoryPolicy: allkeys-lru

# --- Cron Jobs ---
cronJobs:
  - name: morning-brief
    schedule: "30 13 * * 1-5"    # 8:30 AM ET weekdays (UTC)
    command: python -m tasks.cron.morning_brief
    rootDir: apps/api
  - name: position-sync
    schedule: "*/30 13-20 * * 1-5"  # every 30 min during market hours (UTC)
    command: python -m tasks.cron.position_sync
    rootDir: apps/api
  - name: cache-warm
    schedule: "0 14 * * 1-5"     # 9:00 AM ET weekdays (UTC)
    command: python -m tasks.cron.cache_warm
    rootDir: apps/api
  - name: stale-key-check
    schedule: "0 11 * * *"       # 6:00 AM ET daily (UTC)
    command: python -m tasks.cron.stale_key_check
    rootDir: apps/api
```

**Render services:**

| Service | Type | Plan | What |
|---------|------|------|------|
| `wheely-web` | Web Service | Starter ($7/mo) | Next.js frontend, SSR |
| `wheely-api` | Web Service | Starter ($7/mo) | FastAPI, all API endpoints |
| `wheely-worker-screening` | Background Worker | Starter ($7/mo) | Celery: screening + execution queues |
| `wheely-worker-llm` | Background Worker | Starter ($7/mo) | Celery: llm queue |
| `wheely-redis` | Redis | Starter ($10/mo) | Broker, cache, rate limits |
| Cron Jobs | Cron | Included | Morning briefs, position sync, cache warming |

**Note on Render Starter tier:** 512MB RAM per service. Monitor memory usage on the screening worker — screening pipelines with pandas DataFrames + ORATS data can spike. Upgrade to Standard ($25/mo) if OOM kills occur.

**Costs at launch:**

| Service | Cost |
|---------|------|
| Render (web ×2 + worker ×2 + redis) | ~$38/mo |
| Supabase (free tier: 500MB, 50k MAU) | $0 |
| Stripe | 2.9% + 30¢ per transaction |
| FMP | $99/mo |
| ORATS | $99/mo |
| LLM API costs (OpenAI/Anthropic) | ~$20-50/mo depending on usage |
| **Total** | ~$260-290/mo |

**Breakeven:** ~10 premium subscribers at $29/mo covers infrastructure. FMP/ORATS API response caching (Redis TTLs above) is critical — without it, ORATS 20K/month budget is exhausted around 15-20 active users. With caching, extends to ~80-100 active users before needing a plan upgrade.

### Migration path from CLI

CLI tools (`run-strategy`, `run-screener`, `run-call-screener`) remain functional for personal use:

1. FastAPI wraps the same `screen_calls()`, `screen_puts()`, `run_pipeline()` functions
2. CLI reads `config/symbol_list.txt` + `.env` for local use
3. SaaS users' configs/watchlists live in Supabase, API keys in Vault
4. Same screening and strategy engine — two interfaces

### Implementation phases (revised for Render)

**Phase 1 — Monorepo + Render deploy**
- Set up Turborepo monorepo structure
- Move existing screener/strategy code into `apps/api/`
- FastAPI wrapping existing functions
- Write `render.yaml` Blueprint
- Deploy to Render, test with curl over private network

**Phase 2 — Supabase + Auth + Secret Hardening**
- Supabase project, run migrations (including `screening_results`, `vault_access_log`)
- Supabase Auth (email + OAuth)
- Vault integration with envelope encryption (APP_ENCRYPTION_SECRET in Render env)
- RLS policies verified (including new `screening_results` table)
- Vault access audit logging

**Phase 3 — Frontend MVP**
- Next.js app on Render with Supabase Auth
- Dashboard: wheel state + account summary
- Put screener: filter controls + results table + execute
- Call screener: results + execute
- API key settings page (with Alpaca OAuth flow as primary, raw keys as fallback)
- Private network connection to FastAPI verified

**Phase 4 — Stripe billing**
- Stripe products + prices (free/premium)
- Checkout flow (Next.js) + webhook handler (FastAPI ONLY — single target)
- Tier enforcement in FastAPI middleware
- Per-user rate limiting (Redis sliding windows)
- Billing page in frontend

**Phase 5 — LLM integration**
- LiteLLM config + model routing
- Celery tasks on dedicated `llm` queue (Worker 2)
- Screening analysis agent
- Trade reasoning agent
- Redis caching for LLM responses
- Regulatory language guardrails in all agent system prompts

**Phase 6 — Full features**
- Watchlist manager
- Trade journal with AI reasoning
- P&L charts
- History views
- Portfolio risk metrics agent (reports data, no recommendations)
- Market context brief (Render cron job, reports activity, no recommendations)

**Phase 7 — Caching + Scale**
- FMP/ORATS Redis response caching with TTLs
- Cache warming cron job (pre-market)
- Monitor Render Starter memory usage, upgrade workers if needed
- WebSocket for real-time screening progress
- Mobile-responsive layout
- Dark/light theme
- Monitoring + alerting (Sentry, Render metrics)
- Load testing + horizontal scaling plan

**Phase 8 — Scale triggers**

When to upgrade from launch architecture:

| Trigger | Action |
|---------|--------|
| Worker OOM kills | Upgrade Render Starter → Standard ($25/mo per service) |
| ORATS 20K/month approaching | Upgrade ORATS plan or add user-provided keys |
| >50 concurrent screening runs | Add Worker 3 (second screening worker) |
| >100 active users | Supabase free → Pro ($25/mo), add connection pooling |
| Need compliance audit trail | Migrate Vault to AWS Secrets Manager |
