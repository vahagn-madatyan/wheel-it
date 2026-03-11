# Feature Landscape

**Domain:** Wheel Strategy Screener -- v1.1 Fix + Covered Call Screening
**Researched:** 2026-03-11
**Overall confidence:** HIGH

## Context

v1.0 shipped a 10-filter stock screening pipeline with 3 presets, wheel suitability scoring, and Rich output. The pipeline currently produces zero results because (a) `debt_equity` eliminates all 202 Stage 1 survivors (Finnhub data issue or threshold mismatch) and (b) `avg_volume_min` at 2M is too aggressive. v1.1 must fix the pipeline, add options-level screening (IV Rank, earnings, OI/spread), add covered call screening, and differentiate presets properly.

The user's strategy reference document defines a multi-step approach:
- Step 0: Finviz-style stock screening (partially built)
- Step 1: IV Rank >= 30% (ideally >= 50%)
- Step 2: Earnings > 14 days away
- Step 3: OI >= 500, Bid/Ask spread <= $0.10
- Step 4: Sector diversification
- Step 5: Final options chain check (DTE 21-45, delta 0.20-0.30, premium >= $0.50)
- Phase 2: Covered call screening (strike >= cost basis, same DTE/OI/spread rules)

---

## Table Stakes

Features users expect. Missing = product feels incomplete for a wheel strategy screener.

### TS-1: Fix Filter Pipeline (Zero Results Bug)

| Attribute | Detail |
|-----------|--------|
| Why Expected | The screener literally does not work -- zero stocks survive. Users cannot use the tool at all. |
| Complexity | Low-Medium |
| Notes | Two root causes identified: (1) `debt_equity` filter kills all 202 Stage 1 survivors. Finnhub's `totalDebtToEquity` metric returns values in percentage form (e.g., 150.0 for 1.5x D/E), not ratio form. The current threshold of `debt_equity_max: 1.0` would fail anything above 1% D/E. Must verify Finnhub's actual units and adjust thresholds or normalize the value. (2) `avg_volume_min` at 2,000,000 is aggressive -- most wheel-suitable stocks in the $10-$50 range have 500K-1.5M average daily volume. Presets should differentiate: conservative=1M, moderate=500K, aggressive=200K. |

### TS-2: IV Rank / Volatility Percentile Filter

| Attribute | Detail |
|-----------|--------|
| Why Expected | IV Rank is the single most important metric for options sellers. Every serious wheel screener (The Wheel Screener, QuantWheel, Option Samurai, tastytrade) puts IV Rank front and center. Without it, premium sellers are flying blind about whether premiums are rich or cheap relative to history. |
| Complexity | Medium |
| Notes | Two approaches: (A) **True IV Rank** using Alpaca's `implied_volatility` from OptionSnapshot. Requires fetching option snapshots for ATM options across 252 trading days of history to build a percentile. Expensive in API calls. (B) **HV Percentile as proxy** -- compute 30-day HV for each of the last 252 days, then calculate where today's HV sits. The codebase already computes 30-day HV in `compute_historical_volatility()` and already fetches 250 bars. This approach is free, fast, and correlates well with IV Rank for non-earnings periods. **Recommendation:** Use HV Percentile (approach B) because the project already has 250 bars of daily data. Formula: `HV_Percentile = (count of days where rolling_30d_HV < current_30d_HV) / total_days * 100`. Filter threshold: >= 30 (user wants >= 30, ideally >= 50). Add to preset differentiation: conservative >= 50, moderate >= 30, aggressive >= 20. |
| Dependencies | Daily bar data (already fetched, 250 bars). No new API needed. |

### TS-3: Earnings Calendar Check

| Attribute | Detail |
|-----------|--------|
| Why Expected | Selling options into earnings is the number one way wheel traders get burned. Earnings cause IV crush and large price gaps that overwhelm premium collected. Every serious options strategy avoids selling premium within 14 days of earnings. The user's strategy reference explicitly requires earnings > 14 days away. |
| Complexity | Low-Medium |
| Notes | Finnhub already provides an earnings calendar endpoint (`/calendar/earnings`) on the free tier. The project already has a `FinnhubClient` with rate limiting and retry logic. Add an `earnings_calendar(symbol)` method that checks if next earnings date is > N days away. Cost: 1 additional API call per Stage 2 symbol (adds to the existing 2 calls per symbol for profile + metrics). With 1.1s throttle, adds ~1.1s per symbol. For ~200 Stage 1 survivors, that is ~3.5 additional minutes. Acceptable. Filter threshold per presets: conservative >= 21 days, moderate >= 14 days, aggressive >= 7 days. |
| Dependencies | Finnhub API (already integrated). Rate limiter already handles 60 calls/min. |

### TS-4: Options Chain OI and Bid/Ask Spread Filter

| Attribute | Detail |
|-----------|--------|
| Why Expected | OI and bid/ask spread are the primary liquidity checks for options. The user's strategy reference requires OI >= 500 and spread <= $0.10. Without these filters, the screener may recommend stocks whose options are too illiquid to trade at reasonable prices. The existing `core/strategy.py` already filters OI >= 100 for the trading bot, but the screener has no options-level filtering -- it only checks if the stock is "optionable" (boolean). |
| Complexity | Medium |
| Notes | This is a new pipeline stage (call it Stage 3) that runs after the fundamental/technical filters pass. For each surviving stock: (1) Fetch option contracts via Alpaca's `get_option_contracts()` for the DTE range. (2) Fetch option snapshots in batches (existing `BrokerClient.get_option_snapshot()` supports batching). (3) Check that at least one contract meets: OI >= threshold, bid/ask spread <= threshold, delta in range, premium >= minimum. This validates that the stock has tradeable options, not just that it is "optionable." The `Contract.from_contract_snapshot()` already extracts bid_price, ask_price, delta, and oi. Spread = ask_price - bid_price. Threshold per presets: conservative (OI >= 1000, spread <= $0.05), moderate (OI >= 500, spread <= $0.10), aggressive (OI >= 200, spread <= $0.20). |
| Dependencies | Alpaca options API (already integrated). `BrokerClient.get_options_contracts()` and `get_option_snapshot()` already exist. |

### TS-5: Covered Call Screening

| Attribute | Detail |
|-----------|--------|
| Why Expected | The wheel strategy has two legs: selling puts (screened by v1.0) and selling covered calls (not screened at all). The current `sell_calls()` in `core/execution.py` hard-codes the logic with no screening step. The user's strategy reference explicitly defines covered call screening with the same DTE/OI/spread rules, plus strike >= cost basis. A screener that only handles puts is half a wheel screener. |
| Complexity | Medium-High |
| Notes | This requires: (1) A new `run-call-screener` CLI entry point. (2) Input: current assigned positions (symbol + cost basis) from Alpaca positions or user input. (3) For each position: fetch call option chain, filter by strike >= cost basis, apply same OI/spread/delta/premium filters as put screening. (4) Score and rank: use existing `score_options()` logic. (5) Output: Rich table showing symbol, cost basis, recommended strike, DTE, premium, delta, annualized return. (6) Integration: `run-strategy` should optionally use the screener to select calls instead of the current hard-coded `sell_calls()` logic. Key difference from put screening: the universe is small (only assigned positions, typically 1-5 stocks) so no rate limiting concerns. |
| Dependencies | Alpaca positions API (existing). Options chain fetch (existing). Scoring (existing). New CLI entry point (Typer, existing pattern). |

### TS-6: Preset Differentiation for Technicals and Options

| Attribute | Detail |
|-----------|--------|
| Why Expected | The current three presets only differ on fundamental thresholds (market cap, D/E, margin, growth). Technical thresholds (price range, volume, RSI, SMA200) are identical across all three. This makes the presets feel broken -- "aggressive" and "conservative" should produce meaningfully different results. The user's strategy doc expects presets to control filter strictness end-to-end. |
| Complexity | Low |
| Notes | Update presets to differentiate across ALL filter categories. Examples: (Conservative) price $20-$60, volume >= 1M, RSI <= 55, above SMA200 required, DTE 30-45, delta 0.20-0.25. (Moderate) price $10-$80, volume >= 500K, RSI <= 65, above SMA200 required, DTE 21-45, delta 0.20-0.30. (Aggressive) price $5-$150, volume >= 200K, RSI <= 75, above SMA200 optional, DTE 14-60, delta 0.15-0.35. Also add the new filter thresholds (IV rank, earnings days, OI, spread) to each preset. |
| Dependencies | Config schema changes (add new fields to ScreenerConfig Pydantic models). |

---

## Differentiators

Features that set the product apart from generic screeners. Not expected, but valued.

### DF-1: HV vs IV Comparison Display

| Attribute | Detail |
|-----------|--------|
| Value Proposition | Show both HV (computed from bars) and IV (from Alpaca option snapshots) side-by-side. When IV >> HV, options are overpriced relative to realized movement -- ideal for premium sellers. When IV << HV, options are underpriced and selling is less attractive. This gives the user a quick "is premium rich?" signal without requiring paid data. |
| Complexity | Low-Medium |
| Notes | The data is already available: HV from `compute_historical_volatility()`, IV from `snapshot.implied_volatility`. Just need to capture IV during the options chain check (TS-4) and display it in the results table. Add an "IV/HV" ratio column. |

### DF-2: Sector Avoid/Prefer Lists in Presets

| Attribute | Detail |
|-----------|--------|
| Value Proposition | The sector filter currently supports include/exclude lists but presets ship with empty lists. Adding default sector preferences makes presets immediately more useful. Conservative presets should favor Technology, Healthcare, Consumer Staples and exclude Utilities, Real Estate (low premium). Aggressive presets should exclude nothing. |
| Complexity | Low |
| Notes | The `SectorsConfig` model and `filter_sector()` already support this. Just update the YAML preset files. No code changes needed beyond preset content. |

### DF-3: Premium Yield Display in Results Table

| Attribute | Detail |
|-----------|--------|
| Value Proposition | Show the best available put premium as annualized yield alongside each screened stock. This lets users see the actual income potential rather than just a suitability score. Users want to compare "AAPL at 18% annualized" vs "MSFT at 12% annualized." |
| Complexity | Medium |
| Notes | Requires the options chain check (TS-4) to find the best put contract per stock and compute `(bid_price / strike) * (365 / DTE)`. Store the best contract's premium info on the `ScreenedStock` model. Display as "Ann.Yield" column. |

### DF-4: Cost Basis Tracking for Covered Calls

| Attribute | Detail |
|-----------|--------|
| Value Proposition | Track the true cost basis through the wheel cycle: initial assignment price minus accumulated premiums from puts and calls. This matters because a stock assigned at $45 with $3 in premiums collected has an effective basis of $42 -- allowing a $43 covered call strike even though the current price is $41. |
| Complexity | Medium |
| Notes | Requires reading the strategy log JSON to accumulate premiums per symbol across multiple runs. The `StrategyLogger` already records sold puts and calls. Build a `cost_basis_tracker` that reads `logs/strategy_log.json` and computes effective cost basis per symbol. |

### DF-5: Rolling Recommendation

| Attribute | Detail |
|-----------|--------|
| Value Proposition | When a sold option is at 50% profit (user's strategy doc says take profit at 50%), recommend closing and rolling to a new expiration. This is a display-only feature: "AAPL $45P: -52% (roll candidate)". |
| Complexity | Medium |
| Notes | Requires reading current option positions, fetching current prices, computing P&L vs premium received. Display as a section in the screener output or as a separate `--check-rolls` flag. |

---

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Paid IV data subscription (ORATS, Barchart API) | Adds recurring cost dependency, complicates setup, violates "free APIs only" decision. | Use HV Percentile as IV Rank proxy (free, computed from existing bar data) and Alpaca's `implied_volatility` from option snapshots. |
| Backtesting screener results | Completely separate domain. Would double project scope. Historical option pricing data is expensive and not available via free APIs. | Log screening decisions in strategy_log.json for manual review. |
| Real-time streaming screener | WebSocket complexity, rate limit issues. Wheel trades happen weekly, not intraday. | Batch screening on-demand via CLI is sufficient. |
| Custom filter expression language | Over-engineering for a personal tool. Adds parser complexity. | Use YAML config overrides -- users can set any threshold via config file. |
| ML-based stock selection | Black box, hard to debug, requires training data, not relevant for rule-based wheel criteria. | Rule-based filters are transparent and match the user's documented strategy steps. |
| Multi-symbol covered call optimization | Optimizing across multiple assigned positions simultaneously (portfolio-level Greeks) adds massive complexity. | Screen each assigned position independently, rank by annualized return. |
| Alert/notification system | Screener runs on-demand, not continuously. No daemon process exists. | Run `run-screener` manually or via cron. |
| Finviz scraping | Unreliable, violates ToS, breaks frequently. | Finnhub API for fundamentals (already integrated, rate-limited, reliable). |

---

## Feature Dependencies

```
[FIX] TS-1: Fix Filter Pipeline
  |
  v
TS-6: Preset Differentiation ---------> Updated YAML presets
  |
  +---> TS-2: HV Percentile (IV Rank proxy)
  |       |
  |       +---> DF-1: HV vs IV Display (optional, builds on TS-2 + TS-4)
  |
  +---> TS-3: Earnings Calendar Check
  |
  +---> TS-4: Options Chain OI/Spread Filter
          |
          +---> DF-3: Premium Yield Display (optional, builds on TS-4)
          |
          +---> TS-5: Covered Call Screening
                  |
                  +---> DF-4: Cost Basis Tracking (optional, enhances TS-5)
                  |
                  +---> DF-5: Rolling Recommendation (optional, separate concern)
```

**Critical path:** TS-1 (fix) must come first -- nothing else matters if zero stocks pass. TS-6 (presets) should accompany the fix. Then TS-2, TS-3, TS-4 can proceed in parallel (independent filters). TS-5 (covered calls) depends on TS-4 (shared OI/spread logic) but can be developed alongside.

**Parallel work streams:**
- Stream A: TS-1 + TS-6 (fix pipeline + presets)
- Stream B: TS-2 (HV Percentile) -- needs only bar data, no new APIs
- Stream C: TS-3 (earnings) -- needs only Finnhub, independent
- Stream D: TS-4 (options chain check) + TS-5 (covered calls)

---

## MVP Recommendation

### Must Ship (v1.1 scope)

1. **TS-1: Fix Filter Pipeline** -- Without this, the tool is broken. Priority zero.
2. **TS-6: Preset Differentiation** -- Ships with the fix. Makes presets actually different.
3. **TS-2: HV Percentile** -- The strategy doc's Step 1. IV Rank is the #1 metric for options sellers.
4. **TS-3: Earnings Calendar** -- The strategy doc's Step 2. Prevents the #1 cause of wheel losses.
5. **TS-4: OI/Spread Filter** -- The strategy doc's Step 3. Ensures tradeable options exist.
6. **TS-5: Covered Call Screening** -- The strategy doc's Phase 2. Completes the wheel screener.

### Should Ship If Time Allows

7. **DF-2: Sector Avoid/Prefer Presets** -- Near-zero effort, just YAML changes.
8. **DF-3: Premium Yield Display** -- Data is already available from TS-4, just add a column.

### Defer to v1.2+

9. **DF-1: HV vs IV Comparison** -- Nice signal but not critical for screening decisions.
10. **DF-4: Cost Basis Tracking** -- Requires strategy log parsing, separate concern.
11. **DF-5: Rolling Recommendations** -- Useful but not a screening feature per se.

---

## Implementation Notes from Codebase Analysis

### What Already Exists (Reusable)

- `compute_historical_volatility(bars_df, window=30)` in `pipeline.py` -- computes 30-day HV from bar data. Extend to compute rolling HV over 252 days for percentile.
- `BrokerClient.get_options_contracts()` and `get_option_snapshot()` -- already paginate and batch. Reuse for TS-4 options chain checks.
- `Contract.from_contract_snapshot()` -- already extracts bid, ask, delta, OI. Add spread computation.
- `filter_options()` in `core/strategy.py` -- already filters by delta, OI, yield. Can be adapted for screener-side validation.
- `score_options()` in `core/strategy.py` -- reusable for covered call scoring.
- `FinnhubClient._call_with_retry()` -- rate limiting and 429 retry. Extend for earnings endpoint.
- `ScreenerConfig` Pydantic models -- extend with new sections for options chain and earnings thresholds.

### What Needs to Change

- `ScreenedStock` dataclass: add fields for `hv_percentile`, `next_earnings_date`, `days_to_earnings`, `best_put_premium`, `best_put_strike`, `best_put_dte`.
- `ScreenerConfig`: add `options.oi_min`, `options.spread_max`, `options.premium_min`, `options.dte_min`, `options.dte_max`, `options.delta_min`, `options.delta_max`, `options.iv_rank_min`, `earnings.min_days_away`.
- Pipeline: add Stage 3 (options chain validation) after Stage 2 (Finnhub fundamentals).
- `Contract` model: capture `implied_volatility` from `snapshot.implied_volatility` (currently ignored).
- Presets YAML: restructure with differentiated technical, options, and earnings thresholds.
- New CLI: `run-call-screener` entry point in `pyproject.toml`.

### API Budget Impact

Current per-symbol cost (Stage 2): 2 Finnhub calls (profile + metrics) = 2.2s per symbol.
Added per-symbol cost: +1 Finnhub call (earnings) = +1.1s per symbol.
New total: 3.3s per symbol for Finnhub stages.
For ~200 Stage 1 survivors: ~11 minutes total (up from ~7.3 minutes). Acceptable for a batch screener that runs weekly.

Alpaca options chain check (Stage 3) is not rate-limited the same way. For the ~20-50 stocks that survive all filters, fetching option chains adds minimal time.

---

## Sources

- [The Wheel Screener -- IV Rank, IV Percentile, Earnings Date](https://medium.com/option-screener/new-metrics-on-the-wheel-screener-iv-rank-iv-percentile-next-earnings-date-and-last-earnings-07e3e5410ce9) -- Confidence: MEDIUM
- [Barchart IV Rank vs IV Percentile](https://www.barchart.com/education/iv_rank_vs_iv_percentile) -- Confidence: HIGH
- [Schwab: Using Implied Volatility Percentages](https://www.schwab.com/learn/story/using-implied-volatility-percentiles) -- Confidence: HIGH
- [Finnhub Earnings Calendar API](https://finnhub.io/docs/api/earnings-calendar) -- Confidence: HIGH (official docs)
- [Alpaca OptionSnapshot Model](https://alpaca.markets/sdks/python/api_reference/data/models.html) -- Confidence: HIGH (official docs, verified fields: implied_volatility, greeks, latest_quote with bid/ask)
- [QuantWheel Screener Guide](https://quantwheel.com/learn/best-options-screeners/) -- Confidence: MEDIUM
- [Options Cafe Wheel Screener](https://options.cafe/blog/free-wheel-options-screener-find-your-next-trade/) -- Confidence: MEDIUM
- [optionDash: Stocks for Wheel Strategy](https://optiondash.com/how-to-find-stocks-for-the-wheel-strategy/) -- Confidence: MEDIUM
- [Alpaca Wheel Strategy Tutorial](https://alpaca.markets/learn/options-wheel-strategy) -- Confidence: HIGH (official)
- [Option Alpha Wheel Strategy Guide](https://optionalpha.com/blog/wheel-strategy) -- Confidence: MEDIUM
- [SteadyOptions Wheel Strategy](https://steadyoptions.com/articles/the-options-wheel-strategy-wheel-trade-explained-r632/) -- Confidence: MEDIUM
- [Volatility Box IV Rank vs Percentile](https://volatilitybox.com/research/iv-rank-vs-iv-percentile/) -- Confidence: MEDIUM

---
*Feature landscape research for: Wheel Strategy Screener v1.1*
*Researched: 2026-03-11*
