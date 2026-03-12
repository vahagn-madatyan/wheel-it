# Project Research Summary

**Project:** Wheeely Stock Screener v1.1 -- Screener Fix + Covered Call Screening
**Domain:** Options Wheel Strategy Screener (Financial Tooling / CLI)
**Researched:** 2026-03-11
**Confidence:** HIGH

## Executive Summary

Wheeely v1.1 is a fix-then-extend release for a wheel strategy stock screener that currently produces zero results due to two bugs: Finnhub returns `totalDebtToEquity` as a percentage (e.g., 150.0 for 1.5x) while the filter threshold is set to 1.0, and the 2M average volume minimum eliminates 85% of the universe before fundamentals even run. The fix is straightforward -- normalize the Finnhub metric and differentiate preset thresholds. Beyond the fix, four new capabilities are needed to complete the screener: HV-based volatility ranking, earnings calendar filtering, options chain OI/spread validation, and covered call screening. All four build on existing infrastructure with zero new dependencies.

The recommended approach is to fix the pipeline first (diagnostic logging, then threshold/normalization corrections), then layer new filters in cost order: HV Rank computation in Stage 1 (free, uses existing bar data), earnings calendar in Stage 2 (one Finnhub API call for all symbols), options chain validation in a new Stage 2.5 (per-symbol Alpaca calls, run last to minimize volume), and covered call screening as a parallel pipeline reusing put-screening survivors. Every new capability uses packages already installed (alpaca-py 0.43.2, finnhub-python 2.4.27, numpy 2.4.2) and follows established codebase patterns (filter function signatures, BrokerClient dependency injection, cheap-first pipeline ordering).

The primary risks are: (1) Finnhub data quality issues extending beyond D/E to other metrics with inconsistent units or null values, (2) HV Rank diverging from true IV Rank around earnings events (acceptable if labeled honestly and combined with the earnings calendar filter), and (3) options chain API calls at scale pushing pipeline runtime beyond 10 minutes for large survivor sets. All three are mitigable through defensive coding practices documented in the pitfalls research.

## Key Findings

### Recommended Stack

No new dependencies needed. All four capabilities use the existing installed stack. This is a significant finding -- it means zero dependency risk and zero setup friction.

**Core technologies (all existing, verified installed):**
- **alpaca-py 0.43.2**: Option chain data, OI via `get_option_contracts()`, bid/ask/greeks/IV via `get_option_snapshot()` -- all methods already exist in BrokerClient
- **finnhub-python 2.4.27**: Earnings calendar via `earnings_calendar()` method -- free tier, 60/min rate limit, already rate-limited by existing FinnhubClient
- **numpy 2.4.2**: HV Rank percentile computation from rolling 30-day volatility over 252-day lookback -- uses only `np.std`, `np.log`, `np.sqrt`
- **typer 0.24.1 + rich 14.3.3**: New `run-call-screener` CLI entry point following existing `run-screener` pattern

**What NOT to add:** scipy (Black-Scholes IV -- Alpaca already provides IV), yfinance (fragile scraper), any paid IV data service (ORATS, Barchart), Alpha Vantage (25 calls/day too restrictive), ratelimit PyPI package (last release 2019, existing manual throttle works).

See `.planning/research/STACK.md` for full version matrix and API endpoint summary.

### Expected Features

**Must have (table stakes -- all 6 ship in v1.1):**
- **TS-1: Fix Filter Pipeline** -- Zero-result bug caused by D/E percentage format mismatch and 2M volume threshold. Priority zero.
- **TS-2: HV Percentile (IV Rank proxy)** -- The #1 metric for options sellers. Computable from existing 250-bar data with no new API calls.
- **TS-3: Earnings Calendar Check** -- Prevents selling puts into earnings (the #1 cause of wheel losses). Single bulk Finnhub API call.
- **TS-4: Options Chain OI/Spread Filter** -- Validates that tradeable options actually exist. Reuses existing BrokerClient methods.
- **TS-5: Covered Call Screening** -- Completes the wheel (put screening + call screening). Reuses existing `filter_options()` and `score_options()`.
- **TS-6: Preset Differentiation** -- All three presets currently share identical technical thresholds. Must differentiate end-to-end.

**Should have (ship if time allows):**
- **DF-2: Sector Avoid/Prefer Lists** -- Near-zero effort, just YAML changes to existing preset files.
- **DF-3: Premium Yield Display** -- Data already available from TS-4 options chain check, just add a column.

**Defer to v1.2+:**
- HV vs IV comparison display, cost basis tracking from strategy logs, rolling recommendations.

See `.planning/research/FEATURES.md` for full feature landscape, dependency graph, and API budget analysis.

### Architecture Approach

The architecture adds a new Stage 2.5 (options chain validation) to the existing 3-stage pipeline and a parallel covered call pipeline that consumes put-screening survivors. Four new modules are needed (`screener/volatility.py`, `screener/earnings.py`, `screener/options_filter.py`, `screener/call_screener.py`) plus modifications to 7 existing files. The total new code estimate is approximately 360-460 lines across the new modules.

**Major components:**
1. **screener/volatility.py** (NEW) -- Rolling 30-day HV over 252-day window, rank current vs range. ~40-50 LOC.
2. **screener/earnings.py** (NEW) -- Bulk fetch earnings calendar, build symbol-to-date lookup, filter by proximity. ~60-80 LOC.
3. **screener/options_filter.py** (NEW) -- Stage 2.5: validate ATM put OI and bid/ask spread via Alpaca options API. ~80-100 LOC.
4. **screener/call_screener.py** (NEW) -- Covered call pipeline: reuses BrokerClient, Contract model, and strategy scoring functions. ~100-130 LOC.
5. **screener/pipeline.py** (MODIFY) -- Primary modification target: wire HV rank into Stage 1, earnings into Stage 2, new Stage 2.5, pass full BrokerClient.
6. **screener/config_loader.py** (MODIFY) -- Add VolatilityConfig, EarningsConfig, expand OptionsConfig with OI/spread fields.
7. **config/presets/*.yaml** (MODIFY) -- Differentiated thresholds across all filter categories.

**Key patterns to follow:** Filter function signature consistency (all return FilterResult), cheap-first pipeline ordering (HV rank before earnings before options chain), earnings data as lookup table (one API call, not per-symbol), BrokerClient passed to pipeline instead of individual sub-clients.

See `.planning/research/ARCHITECTURE.md` for full data flow diagrams, interface definitions, and anti-patterns.

### Critical Pitfalls

1. **Finnhub D/E is percentage-formatted, not ratio** -- The `totalDebtToEquity` metric returns 150.0 for 1.5x D/E. The threshold of 1.0 kills everything. Fix: add diagnostic logging for 5 known stocks, then normalize (divide by 100 if value > 10) or adjust threshold to match format.

2. **None values treated as filter failure** -- Stocks missing Finnhub metrics (common for small/mid-caps, recent IPOs) are silently eliminated. Fix: implement soft-vs-hard filter categorization where None means "not enough data to disqualify" for non-critical metrics.

3. **HV Rank is not IV Rank** -- HV captures past movement, IV captures expected future movement. They diverge around earnings and events. Fix: label honestly as "HV Rank" or "Volatility Rank (HV-based)", never "IV Rank". Combine with earnings calendar to flag event-driven opportunities.

4. **avg_volume_min at 2M is too restrictive** -- Eliminates 85% of the universe including many wheel-suitable mid-caps. Fix: differentiate presets (Conservative 2M, Moderate 500K, Aggressive 200K) and rely on the new OI filter for options liquidity validation.

5. **Earnings calendar dates are unreliable on free APIs** -- Finnhub has documented inaccuracy issues (GitHub Issue #528). Fix: use 14-day buffer instead of 7-day, flag "unknown" dates as caution rather than pass, prefer the bulk `/calendar/earnings` endpoint.

See `.planning/research/PITFALLS.md` for all 13 pitfalls with phase-specific warnings.

## Implications for Roadmap

Based on research, the features have clear dependency chains that dictate a 4-phase structure. The critical path runs through the pipeline fix, config model updates, options chain integration, and finally covered call screening.

### Phase 1: Debug and Fix Pipeline

**Rationale:** Nothing else matters if zero stocks survive filtering. This is the blocking bug that makes the entire tool unusable. Must be Phase 1.
**Delivers:** A working screener that produces results. Properly differentiated presets. Diagnostic tooling for Finnhub metric validation.
**Addresses:** TS-1 (Fix Filter Pipeline), TS-6 (Preset Differentiation), DF-2 (Sector Avoid/Prefer Lists)
**Avoids:** Pitfall 1 (D/E format mismatch), Pitfall 2 (None-as-failure), Pitfall 4 (volume too restrictive), Pitfall 10 (Finnhub unit inconsistencies), Pitfall 11 (identical preset technicals)
**Stack:** No new dependencies. Config model changes (Pydantic), preset YAML updates.

### Phase 2: HV Rank + Earnings Calendar

**Rationale:** These are the two cheapest new filters (HV Rank is zero API cost; earnings calendar is one API call total). They address the user's strategy Steps 1 and 2 and are independent of each other, enabling parallel development. Both must precede options chain work because they further narrow the survivor set before expensive per-symbol API calls.
**Delivers:** Volatility ranking for premium richness assessment. Earnings proximity filtering to prevent selling into events. Both integrated into the pipeline and displayed in results.
**Addresses:** TS-2 (HV Percentile), TS-3 (Earnings Calendar Check)
**Avoids:** Pitfall 3 (HV != IV -- label honestly), Pitfall 5 (earnings date inaccuracy -- use buffer), Pitfall 7 (HV diverges around events -- combine with earnings filter), Pitfall 13 (bar count off-by-one -- increase to 300)
**Stack:** numpy for HV computation, finnhub-python for earnings calendar. Both existing.

### Phase 3: Options Chain OI/Spread Validation

**Rationale:** Depends on a working pipeline (Phase 1) producing survivors and benefits from the reduced survivor count after HV rank and earnings filtering (Phase 2). This is the most API-intensive new stage and must run last in the pipeline. Establishes the BrokerClient integration pattern that Phase 4 (covered calls) also needs.
**Delivers:** Stage 2.5 in the pipeline: validates that surviving stocks have tradeable options with sufficient OI and tight spreads. Eliminates stocks that are "optionable" in name but illiquid in practice.
**Addresses:** TS-4 (Options Chain OI/Spread Filter), DF-3 (Premium Yield Display)
**Avoids:** Pitfall 6 (rate limits at scale -- filter before fetching, restrict to target strikes/expirations), Pitfall 9 (spread filter too aggressive -- use relative spread percentage)
**Stack:** alpaca-py `get_option_contracts()` and `get_option_snapshot()` (existing BrokerClient methods).

### Phase 4: Covered Call Screening

**Rationale:** Depends on Phase 3's options chain infrastructure and BrokerClient pipeline integration. This is the final feature that completes the wheel screener (put screening + call screening). The universe is small (only assigned positions, typically 1-5 stocks) so rate limiting is a non-issue.
**Delivers:** `run-call-screener` CLI entry point. For each assigned position: best covered call contract with strike, DTE, premium yield, delta, and score. Separate Rich table output.
**Addresses:** TS-5 (Covered Call Screening)
**Avoids:** Pitfall 8 (different criteria than put screener -- separate config section, position-aware strike selection above cost basis)
**Stack:** typer + rich for CLI (existing patterns), core/strategy.py for filter/score reuse.

### Phase Ordering Rationale

- **Phase 1 before everything:** The pipeline is broken. No feature work has value until it produces results.
- **Phase 2 before Phase 3:** HV rank and earnings are cheap filters that reduce the survivor set. Running expensive options chain API calls on a smaller set saves time and avoids rate limit issues.
- **Phase 3 before Phase 4:** Covered call screening reuses the options chain fetch pattern and BrokerClient pipeline integration established in Phase 3.
- **Parallel opportunities within phases:** HV rank and earnings calendar are fully independent (different APIs, different data). Config model updates can parallel the pipeline fix. Display updates come last in each phase.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** Needs a diagnostic spike to determine exact Finnhub D/E format (percentage vs ratio) and None-value prevalence across the Stage 1 survivor set. Research the actual data before committing to a normalization strategy.
- **Phase 3:** Options chain API behavior under load needs validation. The exact Alpaca rate limit for paper accounts (200 req/min documented, but may vary) and the number of requests needed for 50+ survivors should be measured empirically.

Phases with standard patterns (skip research-phase):
- **Phase 2:** Both HV rank computation and Finnhub earnings calendar are well-documented with verified API methods and clear implementation patterns from the stack research.
- **Phase 4:** Pure application layer. Reuses existing BrokerClient, Contract, filter_options(), score_options(). No new API integration needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All packages verified installed via `pip list`. All API methods verified from SDK docs. Zero new dependencies. |
| Features | HIGH | Feature set derived from user's strategy reference document and competitive analysis of wheel screeners. Clear table-stakes vs differentiator separation. |
| Architecture | HIGH | Extends existing 3-stage pipeline with proven patterns. New modules follow established filter/pipeline conventions. All underlying API methods already exist in the codebase. |
| Pitfalls | HIGH | Root cause of zero-result bug identified with code-level evidence. Finnhub data quality issues corroborated by GitHub issues and community reports. HV-vs-IV limitation is well-documented in options literature. |

**Overall confidence:** HIGH

### Gaps to Address

- **Finnhub D/E exact format:** Research strongly suggests percentage format based on elimination pattern, but a diagnostic spike with 5 known stocks is needed to confirm before choosing between normalization vs threshold adjustment.
- **Finnhub None-value prevalence:** Unknown what percentage of Stage 1 survivors lack D/E data. This determines whether to implement pass-on-None or scoring-penalty approach.
- **Free-tier indicative feed accuracy:** Alpaca's free options data uses the "indicative" feed (estimated values, not exchange quotes). Adequate for screening but actual bid/ask spreads may differ from live execution prices. No way to validate without comparing to paid OPRA feed.
- **Earnings calendar coverage for small-caps:** Finnhub earnings dates are reliable for large-caps but accuracy for sub-$1B market cap companies is unverified. The 14-day buffer mitigates but does not eliminate this risk.
- **HV Rank correlation with IV Rank:** The proxy is directionally correct but the actual correlation coefficient is unknown for this universe. Consider validating against Barchart's free IV Rank display for 10 stocks during Phase 2 implementation.

## Sources

### Primary (HIGH confidence)
- [Alpaca-py SDK Options Data Requests](https://alpaca.markets/sdks/python/api_reference/data/option/requests.html) -- OptionChainRequest parameters
- [Alpaca-py SDK Data Models](https://alpaca.markets/sdks/python/api_reference/data/models.html) -- OptionsSnapshot, Quote, OptionsGreeks fields
- [Alpaca Option Chain Endpoint](https://docs.alpaca.markets/reference/optionchain) -- REST endpoint parameters, rate limits
- [Finnhub Earnings Calendar API](https://finnhub.io/docs/api/earnings-calendar) -- Response schema, free tier availability
- [Finnhub Basic Financials API](https://finnhub.io/docs/api/company-basic-financials) -- Metric key documentation
- [Finnhub Python SDK](https://github.com/Finnhub-Stock-API/finnhub-python) -- `earnings_calendar()` method signature
- [Barchart: IV Rank vs IV Percentile](https://www.barchart.com/education/iv_rank_vs_iv_percentile) -- IV Rank computation methodology
- [Schwab: Using Implied Volatility Percentiles](https://www.schwab.com/learn/story/using-implied-volatility-percentiles) -- IV Percentile vs IV Rank

### Secondary (MEDIUM confidence)
- [Finnhub Earnings Calendar Accuracy Issue #528](https://github.com/finnhubio/Finnhub-API/issues/528) -- Documented date inaccuracy for specific stocks
- [Finnhub Metric Data Quality Issue #337](https://github.com/finnhubio/Finnhub-API/issues/337) -- Metric value inconsistency reports
- [Robot Wealth: Exploring the Finnhub API](https://robotwealth.com/finnhub-api/) -- D/E format analysis
- [The Wheel Screener](https://medium.com/option-screener/new-metrics-on-the-wheel-screener-iv-rank-iv-percentile-next-earnings-date-and-last-earnings-07e3e5410ce9) -- Competitive feature analysis
- [QuantWheel Screener Guide](https://quantwheel.com/learn/best-options-screeners/) -- Feature landscape
- [Option Alpha Wheel Strategy Guide](https://optionalpha.com/blog/wheel-strategy) -- Domain context
- [Apple D/E from MacroTrends](https://www.macrotrends.net/stocks/charts/AAPL/apple/debt-equity-ratio) -- Reference values for D/E verification

### Tertiary (LOW confidence)
- [TradingView: IV Rank VIXFix HV Proxy](https://www.tradingview.com/script/HyEYHf6d-IV-Rank-tasty-style-VIXFix-HV-Proxy/) -- Alternative HV proxy approach (community script)
- [Alpaca Rate Limits](https://alpaca.markets/support/usage-limit-api-calls) -- 200 req/min for paper (may vary by plan)

---
*Research completed: 2026-03-11*
*Ready for roadmap: yes*

# Architecture Patterns

**Domain:** Screener Fix + IV Rank / Earnings / OI-Spread / Covered Call Screening
**Researched:** 2026-03-11
**Confidence:** HIGH

## Executive Summary

The four new features (IV Rank approximation, earnings calendar check, options OI/spread filtering, covered call screening) integrate cleanly into the existing 3-stage pipeline architecture. The key architectural insight is that the current pipeline already fetches 250 days of daily bars -- enough for HV Rank computation -- and the existing `core/` options infrastructure (`BrokerClient`, `Contract`, `strategy.py`) provides a complete foundation for options chain inspection.

The recommended approach adds a **Stage 2.5** (options chain validation) between the current Finnhub stage and scoring, plus a **parallel covered call pipeline** that reuses Stage 1-2 survivors filtered through call-specific criteria.

## Recommended Architecture

### Current Pipeline (v1.0)

```
Universe (14K+)
    |
    v
Stage 1: Alpaca Technicals (free, batch)
    price_range, avg_volume, rsi, sma200
    |  ~200-500 survivors
    v
Stage 2: Finnhub Fundamentals (60/min rate limit)
    market_cap, debt_equity, net_margin, sales_growth, sector, optionable
    |  ~20-80 survivors
    v
Stage 3: Scoring + Sort
    compute_wheel_score() -> Rich table output
```

### Proposed Pipeline (v1.1)

```
Universe (14K+)
    |
    v
Stage 1: Alpaca Technicals (free, batch) -- MODIFY
    price_range, avg_volume, rsi, sma200
    + NEW: hv_rank (computed from existing 250 bars, no new API calls)
    |  ~200-500 survivors
    v
Stage 2: Finnhub Fundamentals (60/min rate limit) -- MODIFY
    market_cap, debt_equity, net_margin, sales_growth, sector, optionable
    + NEW: earnings_proximity (Finnhub earnings_calendar endpoint)
    |  ~20-80 survivors
    v
Stage 2.5: Options Chain Validation (Alpaca options API) -- NEW
    open_interest_min, bid_ask_spread_max
    (Fetch ATM put snapshot for each survivor, check OI + spread)
    |  ~15-60 survivors
    v
Stage 3: Scoring + Sort -- MODIFY
    Updated compute_wheel_score() with IV rank and OI quality components
    |
    +---> Put screening results (existing path)
    |
    +---> Covered call screening results (NEW parallel path)
```

### Component Boundaries

| Component | Responsibility | Communicates With | Status |
|-----------|---------------|-------------------|--------|
| `screener/pipeline.py` | Orchestrate stages, wire data flow | All screener modules | MODIFY: add Stage 2.5, HV rank, earnings |
| `screener/volatility.py` | HV rank computation (rolling 30-day HV over 252 days, rank current vs range) | pipeline.py | NEW |
| `screener/earnings.py` | Earnings proximity filter using Finnhub | finnhub_client.py | NEW |
| `screener/options_filter.py` | OI and bid/ask spread validation via Alpaca options chain | core/broker_client.py | NEW |
| `screener/call_screener.py` | Covered call pipeline: take survivors, find best call contracts | core/broker_client.py, core/strategy.py | NEW |
| `screener/config_loader.py` | YAML config with new sections for HV rank, earnings, OI thresholds | presets | MODIFY |
| `screener/display.py` | New columns for HV rank, earnings proximity, call premium | pipeline results | MODIFY |
| `screener/finnhub_client.py` | Add `earnings_calendar()` method | Finnhub API | MODIFY |
| `models/screened_stock.py` | New fields for hv_rank, earnings_date, oi, spread, call data | pipeline | MODIFY |
| `config/presets/*.yaml` | New threshold sections | config_loader | MODIFY |
| `scripts/run_call_screener.py` | Standalone CLI entry point for call screening | call_screener | NEW |

### Data Flow

#### HV Rank (Stage 1 addition -- zero new API calls)

```
Existing 250-bar daily DataFrame (already fetched in Step 3)
    |
    v
screener/volatility.py: compute_hv_rank(bars_df, window=30)
    1. Compute rolling 30-day HV for each day in the 252-bar window
    2. current_hv = last rolling HV value (this is hv_30 already computed)
    3. hv_high = max rolling HV over the window
    4. hv_low = min rolling HV over the window
    5. hv_rank = (current_hv - hv_low) / (hv_high - hv_low) * 100
    |
    v
ScreenedStock.hv_rank: float (0-100)
    |
    v
filter_hv_rank(stock, config) -- pass if hv_rank >= config.volatility.hv_rank_min
```

**Why HV Rank instead of true IV Rank:** True IV Rank requires 52 weeks of historical implied volatility data. Alpaca's OptionSnapshot provides current IV but no historical IV time series. Paid services (ORATS, IVolatility) provide this but violate the free-API-only constraint. HV Rank using 30-day rolling historical volatility over a 252-day window is a well-established proxy that correlates meaningfully with IV Rank for wheel strategy screening purposes.

**Confidence:** HIGH -- the 250 bars already fetched are sufficient for 252-trading-day HV rank computation (250 prices yields 249 returns, enough for a rolling 30-day window over ~220 data points).

#### Earnings Calendar (Stage 2 addition -- 1 Finnhub API call per batch)

```
Finnhub earnings_calendar(from=today, to=today+45, symbol="")
    |  Returns: [{symbol, date, epsEstimate, ...}, ...]
    v
Build lookup: earnings_map = {symbol: nearest_earnings_date}
    |  One API call covers ALL symbols in the date range
    v
For each Stage 2 survivor:
    earnings_date = earnings_map.get(stock.symbol)
    days_to_earnings = (earnings_date - today).days if found
    |
    v
filter_earnings_proximity(stock, config)
    FAIL if days_to_earnings <= config.earnings.min_days_before_earnings
    (Default: fail if earnings within 7 days -- avoid selling puts into earnings)
```

**Key insight:** The earnings calendar endpoint accepts a date range and returns ALL symbols reporting in that range. This means a single API call (counting as 1 against the 60/min limit) provides earnings data for the entire universe. No per-symbol API calls needed.

**Confidence:** HIGH -- Finnhub's `earnings_calendar(_from, to)` is documented and available on the free tier. The Python SDK exposes it as `finnhub_client.earnings_calendar(_from="YYYY-MM-DD", to="YYYY-MM-DD")`.

#### Options OI & Spread Filter (New Stage 2.5)

```
For each Stage 2 survivor (20-80 symbols):
    |
    v
BrokerClient.get_options_contracts([symbol], 'put')
    + BrokerClient.get_option_snapshot([contract_symbols])
    |  Returns: contracts with OI + snapshots with bid/ask
    v
Find ATM put (strike nearest to stock price, 20-45 DTE)
    |
    v
Check:
    1. OI >= config.options.min_open_interest (default 100)
    2. spread = (ask - bid) / mid_price
       spread <= config.options.max_spread_pct (default 0.10 = 10%)
    |
    v
filter_options_oi(stock, config) -- PASS/FAIL
filter_options_spread(stock, config) -- PASS/FAIL
```

**Integration with existing code:** `BrokerClient.get_options_contracts()` and `BrokerClient.get_option_snapshot()` already exist and are battle-tested in `core/execution.py`. The new `screener/options_filter.py` reuses these exact methods. No new API wrapper code needed.

**Batching strategy:** The option snapshot API accepts batches of up to 100 symbols. For 20-80 survivors, this means 1-2 API calls for all snapshots. Combined with contract fetching (paginated at 1000), the total API load is modest.

**Confidence:** HIGH -- this reuses existing, working BrokerClient methods.

#### Covered Call Screening (Parallel pipeline)

```
Put screening survivors (from main pipeline)
    |
    v
screener/call_screener.py: screen_covered_calls(survivors, broker_client, config)
    |
    For each survivor:
    |   1. BrokerClient.get_options_contracts([symbol], 'call')
    |   2. BrokerClient.get_option_snapshot([call_symbols])
    |   3. Build Contract objects via Contract.from_contract_snapshot()
    |   4. core/strategy.py: filter_options(contracts, min_strike=stock.price)
    |   5. core/strategy.py: score_options(filtered)
    |   6. Select top call per symbol
    |
    v
CallScreenResult (new dataclass or extension of ScreenedStock):
    symbol, strike, expiration, delta, bid, premium_yield, score
    |
    v
Display: separate Rich table for call candidates
    or combined table with put + call columns
```

**Maximum code reuse:** The covered call screening path reuses three existing components directly:
1. `BrokerClient.get_options_contracts(symbols, 'call')` -- existing method
2. `Contract.from_contract_snapshot()` -- existing constructor
3. `core/strategy.py: filter_options()` and `score_options()` -- existing pure functions

The only new code is the orchestration layer (`call_screener.py`) that wires these together for screening display rather than order execution.

**Important difference from execution:** `core/execution.py:sell_calls()` takes a single symbol with a known purchase price (for min_strike). The call screener takes multiple survivors and uses current market price as min_strike. This is a thin wrapper, not a rewrite.

**Confidence:** HIGH -- all underlying API methods and strategy functions already exist.

## New Modules (4 new files)

### 1. `screener/volatility.py` -- HV Rank Computation

**Purpose:** Compute rolling historical volatility and rank current HV within its 52-week range.

**Interface:**
```python
def compute_hv_rank(bars_df: pd.DataFrame, window: int = 30) -> float | None:
    """Return HV rank (0-100) or None if insufficient data.

    Args:
        bars_df: Daily OHLCV bars (250+ rows).
        window: Rolling HV window in trading days.

    Returns:
        HV rank as percentage, or None if < window+1 bars.
    """
```

**Depends on:** numpy, pandas (already installed)
**Used by:** `pipeline.py` (called alongside existing `compute_historical_volatility()`)
**Lines of code estimate:** ~40-50

### 2. `screener/earnings.py` -- Earnings Calendar Filter

**Purpose:** Check if a stock has earnings within N days, fail if too close.

**Interface:**
```python
def fetch_earnings_calendar(
    finnhub_client: FinnhubClient,
    from_date: str,
    to_date: str,
) -> dict[str, datetime.date]:
    """Fetch earnings dates, return {symbol: nearest_date} map."""

def filter_earnings_proximity(
    stock: ScreenedStock,
    config: ScreenerConfig,
    earnings_map: dict[str, datetime.date],
) -> FilterResult:
    """Fail if earnings within config.earnings.min_days_before_earnings."""
```

**Depends on:** `screener/finnhub_client.py` (for API access)
**Used by:** `pipeline.py` (called during Stage 2, reuses same FinnhubClient)
**Lines of code estimate:** ~60-80

### 3. `screener/options_filter.py` -- OI & Spread Validation

**Purpose:** Validate that ATM put options have sufficient liquidity (OI + tight spread).

**Interface:**
```python
def validate_options_liquidity(
    symbol: str,
    stock_price: float,
    broker_client: BrokerClient,
    config: ScreenerConfig,
) -> tuple[FilterResult, FilterResult, dict]:
    """Check OI and spread for ATM put. Returns (oi_result, spread_result, options_data)."""
```

**Depends on:** `core/broker_client.py` (existing methods)
**Used by:** `pipeline.py` (Stage 2.5)
**Lines of code estimate:** ~80-100

### 4. `screener/call_screener.py` -- Covered Call Pipeline

**Purpose:** Screen best covered call opportunities for put-screening survivors.

**Interface:**
```python
def screen_covered_calls(
    survivors: list[ScreenedStock],
    broker_client: BrokerClient,
    config: ScreenerConfig,
    on_progress: Callable | None = None,
) -> list[CallCandidate]:
    """For each survivor, find the best covered call contract."""
```

**Depends on:** `core/broker_client.py`, `core/strategy.py`, `models/contract.py`
**Used by:** `scripts/run_call_screener.py` (new CLI), `pipeline.py` (optional integration)
**Lines of code estimate:** ~100-130

### 5. `scripts/run_call_screener.py` -- CLI Entry Point

**Purpose:** Standalone CLI for covered call screening: `run-call-screener`.

**Interface:** Follows existing `run_screener.py` pattern with Typer.
**Lines of code estimate:** ~80-100

## Existing Modules That Need Modification

### 1. `screener/pipeline.py` -- Orchestrator (PRIMARY MODIFICATION TARGET)

**Changes:**
- Add HV rank computation in Step 4 (alongside existing `compute_historical_volatility()`)
- Add `filter_hv_rank()` to Stage 1 filter list in `run_stage_1_filters()`
- Fetch earnings calendar once before Stage 2 loop (single API call)
- Add `filter_earnings_proximity()` to Stage 2 filter list in `run_stage_2_filters()`
- Add new Stage 2.5 between Stage 2 and scoring: options chain validation loop
- Pass `BrokerClient` to pipeline (currently only uses `trade_client` and `stock_client`)

**Risk:** Medium -- this is the most invasive change. The pipeline orchestrator grows from 3 stages to 4. However, the existing stage pattern (run filters, append results, check all passed) is well-established and the new stages follow the same pattern.

### 2. `screener/config_loader.py` -- Config Models

**Changes:**
- Expand `OptionsConfig` with new fields:
  ```python
  class OptionsConfig(BaseModel):
      optionable: bool = True
      min_open_interest: int = 100
      max_spread_pct: float = 0.10
  ```
- Add new config sections:
  ```python
  class VolatilityConfig(BaseModel):
      hv_rank_min: float = 20.0   # Minimum HV rank (0-100)

  class EarningsConfig(BaseModel):
      min_days_before_earnings: int = 7
      check_enabled: bool = True
  ```
- Add these to `ScreenerConfig`:
  ```python
  class ScreenerConfig(BaseModel):
      # ... existing fields ...
      volatility: VolatilityConfig = VolatilityConfig()
      earnings: EarningsConfig = EarningsConfig()
  ```

### 3. `screener/finnhub_client.py` -- Add Earnings Calendar Method

**Changes:**
- Add `earnings_calendar()` method:
  ```python
  def earnings_calendar(self, from_date: str, to_date: str) -> list[dict]:
      """Fetch earnings calendar for date range."""
      return self._call_with_retry(
          lambda: self._client.earnings_calendar(
              _from=from_date, to=to_date, symbol="", international=False
          ),
          symbol="",
          endpoint="earnings_calendar",
      )
  ```

**Risk:** Low -- follows existing `_call_with_retry` pattern exactly.

### 4. `models/screened_stock.py` -- New Fields

**Changes:**
- Add fields:
  ```python
  # Volatility (v1.1)
  hv_rank: Optional[float] = None        # HV rank (0-100)

  # Earnings (v1.1)
  earnings_date: Optional[str] = None     # Next earnings date
  days_to_earnings: Optional[int] = None  # Days until earnings

  # Options chain validation (v1.1)
  atm_put_oi: Optional[int] = None        # ATM put open interest
  atm_put_spread: Optional[float] = None  # ATM put bid/ask spread %

  # Covered call data (v1.1)
  best_call_symbol: Optional[str] = None
  best_call_strike: Optional[float] = None
  best_call_premium: Optional[float] = None
  best_call_delta: Optional[float] = None
  best_call_score: Optional[float] = None
  ```

**Risk:** Low -- additive only, all new fields are Optional with None defaults. No existing code breaks.

### 5. `screener/display.py` -- New Table Columns

**Changes:**
- Add columns to results table: HV Rank, Earnings, OI, Spread
- Optionally add call data columns or a separate call results table
- Update `render_stage_summary()` with Stage 2.5 count
- Update `render_filter_breakdown()` with new filter names

### 6. `config/presets/*.yaml` -- Updated Thresholds

**Changes:**
- Add new sections to all three presets with differentiated values:
  - Conservative: `hv_rank_min: 30`, `min_days_before_earnings: 14`, `min_open_interest: 500`, `max_spread_pct: 0.05`
  - Moderate: `hv_rank_min: 20`, `min_days_before_earnings: 7`, `min_open_interest: 100`, `max_spread_pct: 0.10`
  - Aggressive: `hv_rank_min: 10`, `min_days_before_earnings: 3`, `min_open_interest: 50`, `max_spread_pct: 0.15`

### 7. `pyproject.toml` -- New CLI Entry Point

**Changes:**
- Add: `run-call-screener = "scripts.run_call_screener:main"`

## Patterns to Follow

### Pattern 1: Filter Function Signature

All existing filters follow this signature. New filters must follow it exactly.

```python
def filter_hv_rank(stock: ScreenedStock, config: ScreenerConfig) -> FilterResult:
    """Check if HV rank meets minimum threshold."""
    # ... validation + comparison ...
    return FilterResult(
        filter_name="hv_rank",
        passed=True/False,
        actual_value=stock.hv_rank,
        threshold=config.volatility.hv_rank_min,
        reason="...",
    )
```

**Why:** Consistent filter signature enables uniform pipeline stage runners, uniform display in waterfall breakdown, and uniform test patterns.

### Pattern 2: Cheap-First Pipeline Ordering

New filters must be inserted in cost order:
1. HV Rank -- computed from already-fetched bar data (zero API cost) -- goes in Stage 1
2. Earnings calendar -- single batch Finnhub API call -- goes at start of Stage 2
3. OI/Spread -- per-symbol Alpaca options API call -- goes after Stage 2 (new Stage 2.5)

**Why:** The entire pipeline design optimizes for minimizing expensive API calls. OI/spread checks use per-symbol option chain fetches, so they must run last (only on 20-80 survivors, not 14K+ universe).

### Pattern 3: BrokerClient Dependency Injection

The pipeline currently receives `trade_client` and `stock_client` directly. Stage 2.5 needs the full `BrokerClient` for `get_options_contracts()` and `get_option_snapshot()`. Two approaches:

**Recommended:** Pass `BrokerClient` to `run_pipeline()` instead of individual clients. The pipeline extracts `trade_client` and `stock_client` internally. This is cleaner than adding a third parameter.

```python
def run_pipeline(
    broker_client: BrokerClient,   # Changed: full client instead of 2 sub-clients
    finnhub_client: FinnhubClient,
    config: ScreenerConfig,
    ...
) -> list[ScreenedStock]:
```

**Why:** The existing call sites (`run_screener.py`, `run_strategy.py`) already create a full `BrokerClient` and destructure it. Passing the full client is simpler.

### Pattern 4: Earnings Data as Lookup Table

Earnings data should be fetched once and passed as a dict, not fetched per-symbol.

```python
# In run_pipeline(), before Stage 2 loop:
earnings_map = fetch_earnings_calendar(finnhub_client, today, today + 45_days)

# In run_stage_2_filters():
filter_earnings_proximity(stock, config, earnings_map)
```

**Why:** Avoids N API calls for N symbols. One call covers all symbols in the date range.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Per-Symbol IV Fetching for IV Rank

**What:** Fetching 252 days of historical option snapshots per symbol to compute true IV Rank.
**Why bad:** Alpaca doesn't provide historical IV time series for free. This would require a paid data provider (ORATS, IVolatility) or 252 daily snapshot recordings over time.
**Instead:** Use HV Rank as a proxy. It's computable from data already being fetched (250 daily bars) and correlates meaningfully with IV Rank for screening purposes.

### Anti-Pattern 2: Options Chain Fetch Before Fundamentals

**What:** Moving OI/spread checks to Stage 1 (before Finnhub fundamentals).
**Why bad:** Options chain fetches are per-symbol API calls. Running them on 200-500 Stage 1 survivors instead of 20-80 Stage 2 survivors would 5-10x the API load and runtime.
**Instead:** Keep OI/spread checks as Stage 2.5, after fundamentals have narrowed the pool.

### Anti-Pattern 3: Monolithic Call Screener

**What:** Building covered call screening as a completely separate pipeline with its own universe fetch, bar computation, and filtering.
**Why bad:** Duplicates ~80% of the put screening pipeline. Double API calls, double runtime.
**Instead:** Call screening should consume the put pipeline's survivors and only add call-specific logic (find best call contract per symbol).

### Anti-Pattern 4: Storing Earnings Data Persistently

**What:** Creating a local database or cache of earnings dates to avoid API calls on subsequent runs.
**Why bad:** Earnings dates change (postponements, announcements). Stale data leads to selling puts into earnings. The existing codebase explicitly avoids local databases.
**Instead:** Fetch fresh earnings data on every run. It's a single API call.

## Scalability Considerations

| Concern | Current (v1.0) | After v1.1 | Mitigation |
|---------|----------------|------------|------------|
| Finnhub rate limit | ~200 calls (2 per Stage 2 symbol) | ~201 calls (+1 for earnings) | Negligible increase |
| Alpaca options API | 0 calls | 20-80 contract fetches + 1-2 snapshot batches | Acceptable for <100 survivors |
| Pipeline runtime | ~4 min (Finnhub bottleneck) | ~5-6 min (+options chain) | Still within interactive CLI tolerance |
| Memory | ~14K ScreenedStock objects | Same + a few new Optional fields | Negligible |
| New CLI commands | 2 (run-strategy, run-screener) | 3 (+run-call-screener) | Clean separation |

## Build Order (Dependency-Driven)

The features have specific dependency chains that dictate build order:

| Order | Component | Depends On | Rationale |
|-------|-----------|------------|-----------|
| 1 | Fix existing pipeline (debug zero-results bug) | Nothing | Must work before adding features. The debt_equity and avg_volume thresholds need adjustment first. |
| 2a | `screener/volatility.py` + HV rank filter | Existing bar data | Zero new API calls. Pure computation on existing data. Can be built and tested independently. |
| 2b | Config model updates (`config_loader.py`, presets) | Nothing | New Pydantic fields and preset values. Foundation for all other features. |
| 3 | `screener/earnings.py` + `finnhub_client.py` update | FinnhubClient | One new Finnhub method + filter logic. Independent of other features. |
| 4 | `screener/options_filter.py` (Stage 2.5) | BrokerClient | Requires pipeline refactor to pass full BrokerClient. Depends on steps 1-2 being done. |
| 5 | Pipeline integration (wire all new stages) | Steps 2-4 | Orchestration. All new filters/stages wired into `run_pipeline()`. |
| 6 | `screener/call_screener.py` + CLI | Steps 4-5 + core/strategy.py | Depends on pipeline survivors + BrokerClient access. Reuses existing strategy functions. |
| 7 | Display updates + preset tuning | Steps 5-6 | Output layer. Must come after data is flowing through pipeline. |

**Critical path:** 1 -> 2b -> 4 -> 5 -> 6 -> 7
**Parallel opportunities:** Steps 2a and 2b can be built simultaneously. Step 3 can parallel step 4.

## Sources

- [Alpaca Options API - Get Option Contracts](https://docs.alpaca.markets/reference/get-options-contracts)
- [Alpaca Option Chain](https://docs.alpaca.markets/reference/optionchain)
- [Alpaca-py SDK Models (OptionSnapshot)](https://alpaca.markets/sdks/python/api_reference/data/models.html)
- [Finnhub Earnings Calendar API](https://finnhub.io/docs/api/earnings-calendar)
- [Finnhub Python SDK](https://github.com/Finnhub-Stock-API/finnhub-python)
- [Finnhub Rate Limits](https://finnhub.io/docs/api/rate-limit)
- [IV Rank vs IV Percentile - Barchart](https://www.barchart.com/education/iv_rank_vs_iv_percentile)
- [Using Implied Volatility Rankings - Schwab](https://www.schwab.com/learn/story/using-implied-volatility-percentiles)

---
*Architecture research for: Screener Fix + Covered Call Screening (v1.1)*
*Researched: 2026-03-11*

# Technology Stack: v1.1 Additions

**Project:** Wheeely Stock Screener - Screener Fix + Covered Call Screening
**Researched:** 2026-03-11
**Scope:** NEW capabilities only (IV Rank, earnings calendar, OI/spread filtering, covered call screening)

## Executive Summary

No new dependencies needed. All four new capabilities can be built using existing packages: `finnhub-python` (earnings calendar), `alpaca-py` (options chain with OI/spread/IV), `numpy` (HV percentile rank computation), and `typer`/`rich` (covered call CLI). The project already has everything installed.

## Existing Stack (Validated, DO NOT change)

| Package | Installed Version | Status |
|---------|-------------------|--------|
| alpaca-py | 0.43.2 | Current latest |
| finnhub-python | 2.4.27 | Current latest |
| ta | 0.11.0 | Current latest |
| pydantic | 2.12.5 | Current latest |
| rich | 14.3.3 | Current latest |
| typer | 0.24.1 | Current latest |
| numpy | 2.4.2 | Current latest |
| pandas | 3.0.1 | Current latest |
| PyYAML | 6.0.3 | Current latest |

**Confidence: HIGH** -- All versions verified against installed packages via `pip list`.

## New Capability 1: IV Rank Approximation

### Approach: HV Percentile Rank (no new dependencies)

**Recommendation:** Compute a Historical Volatility Rank as a proxy for IV Rank. This uses only `numpy` and the daily bar data already fetched by `screener/market_data.py`.

**Why not true IV Rank:**
- True IV Rank requires 252 days of historical implied volatility data per symbol
- No free API provides historical IV time series (Barchart, IVolatility, ORATS all require paid plans)
- Alpaca's `OptionsSnapshot.implied_volatility` gives current IV for a single contract, not a 52-week time series
- Computing IV from options prices via Black-Scholes is possible but requires iterating over 252 days of historical option chain data, which is not available on any free API

**Why HV Percentile Rank works:**
- Historical volatility and implied volatility are highly correlated (IV mean-reverts toward HV)
- HV Rank captures the same signal: "Is volatility high or low relative to recent history?"
- The existing `compute_historical_volatility()` function in `screener/market_data.py` already computes 30-day annualized HV from daily bars
- Extending to a 252-day rolling window for percentile ranking requires only `numpy` operations on data already in memory

**Implementation pattern:**
```python
# In screener/market_data.py -- extend existing function
def compute_hv_rank(bars_df: pd.DataFrame, hv_window: int = 30, lookback: int = 252) -> float | None:
    """Percentile rank of current HV within its 252-day range.

    Returns 0-100 float. High values = volatility is elevated.
    Uses only numpy (already imported) and the bars DataFrame (already fetched).
    """
    if len(bars_df) < lookback + hv_window:
        return None

    close = bars_df["close"].values
    log_returns = np.log(close[1:] / close[:-1])

    # Rolling HV for each day in lookback
    hvs = []
    for i in range(len(log_returns) - hv_window + 1):
        window_returns = log_returns[i : i + hv_window]
        daily_std = np.std(window_returns, ddof=1)
        hvs.append(daily_std * np.sqrt(252))

    current_hv = hvs[-1]
    lookback_hvs = hvs[-lookback:] if len(hvs) >= lookback else hvs
    rank = sum(1 for hv in lookback_hvs if hv <= current_hv) / len(lookback_hvs) * 100
    return round(rank, 1)
```

**Integration point:** `screener/market_data.py` already has `compute_historical_volatility()`. Add `compute_hv_rank()` next to it. The `run_pipeline()` in `screener/pipeline.py` already calls `compute_historical_volatility(bars[sym])` -- add a parallel call for HV rank using the same bars data.

**Data requirement:** 250 daily bars are already fetched by `fetch_daily_bars()` with `num_bars=250`. For proper 252-day lookback, may need to bump to `num_bars=300` to ensure enough trading days after weekends/holidays.

**Confidence: HIGH** -- Uses only numpy (installed), extends existing pattern, no API calls needed.

### Alternative Considered: Alpaca Current IV as Standalone Signal

Alpaca's `OptionsSnapshot.implied_volatility` returns current IV for each option contract. This could be used as a standalone volatility signal without ranking, but:
- It's a point-in-time value with no historical context
- Without the "rank" component, you can't tell if IV=30% is high or low for that stock
- **Verdict:** Useful as a supplemental display field, not as a filter replacement for IV Rank

## New Capability 2: Earnings Calendar Check

### Approach: Finnhub `earnings_calendar` endpoint (no new dependencies)

**Recommendation:** Use the existing `finnhub-python` SDK's `earnings_calendar()` method. It is available on the free tier and already installed.

**SDK method (verified from GitHub README):**
```python
finnhub_client.earnings_calendar(
    _from="2026-03-11",  # start date
    to="2026-04-11",     # end date
    symbol="AAPL",       # optional: filter to specific symbol
    international=False   # US only
)
```

**Response structure (verified from Finnhub docs):**
```python
{
    "earningsCalendar": [
        {
            "date": "2026-04-25",      # earnings release date
            "epsActual": None,          # null for upcoming
            "epsEstimate": 1.52,        # consensus estimate
            "hour": "amc",             # "bmo"=before market open, "amc"=after close, "dmh"=during hours
            "quarter": 2,
            "revenueActual": None,
            "revenueEstimate": 94200000000,
            "symbol": "AAPL",
            "year": 2026
        }
    ]
}
```

**Integration point:** Add an `earnings_within_days()` method to the existing `FinnhubClient` class in `screener/finnhub_client.py`. This method wraps the SDK call and returns `True`/`False` + the earnings date.

**Rate limit consideration:** Each symbol-specific earnings check = 1 API call against Finnhub's 60/min limit. The existing `_throttle()` and `_call_with_retry()` methods in `FinnhubClient` handle this automatically. Since earnings checking happens in Stage 2 (only for stocks that passed Stage 1 filters), the volume should be manageable (typically 100-300 symbols).

**Optimization:** Instead of calling per-symbol, fetch the bulk earnings calendar for the next N days (e.g., 30 days) in a single API call (no symbol filter), then check each stock against the result dict. This reduces 200+ calls to 1 call.

```python
# Bulk fetch approach (1 API call instead of 200+)
all_earnings = finnhub_client.earnings_calendar(_from="2026-03-11", to="2026-04-11")
earnings_dates = {e["symbol"]: e["date"] for e in all_earnings.get("earningsCalendar", [])}
# Then check: if stock.symbol in earnings_dates and within N days: flag it
```

**Confidence: HIGH** -- Verified SDK method exists, confirmed free tier access, uses existing FinnhubClient patterns.

### Alternative Considered: Alpha Vantage Earnings Calendar

Alpha Vantage has an `EARNINGS_CALENDAR` endpoint on the free tier. However:
- Requires a separate API key and client
- Free tier limited to 25 calls/day (vs. Finnhub's 60/min)
- Would add unnecessary API dependency when Finnhub already covers this
- **Verdict:** Do not use. Finnhub is already integrated and sufficient.

## New Capability 3: Options Chain OI and Bid/Ask Spread Filtering

### Approach: Alpaca `get_option_chain()` method (no new dependencies)

**Recommendation:** Use `alpaca-py`'s `OptionHistoricalDataClient.get_option_chain()` with `OptionChainRequest` to fetch the full option chain for each underlying. This returns `OptionsSnapshot` objects containing all needed fields.

**Available fields per contract (verified from Alpaca SDK docs):**

| Field | Location in OptionsSnapshot | Available on Free Tier |
|-------|---------------------------|----------------------|
| Open Interest | Via `GetOptionContractsRequest` (trading API) | Yes |
| Bid Price | `snapshot.latest_quote.bid_price` | Yes (indicative feed) |
| Ask Price | `snapshot.latest_quote.ask_price` | Yes (indicative feed) |
| Bid Size | `snapshot.latest_quote.bid_size` | Yes (indicative feed) |
| Ask Size | `snapshot.latest_quote.ask_size` | Yes (indicative feed) |
| Implied Volatility | `snapshot.implied_volatility` | Yes (indicative feed) |
| Delta | `snapshot.greeks.delta` | Yes (indicative feed) |
| Gamma | `snapshot.greeks.gamma` | Yes (indicative feed) |
| Theta | `snapshot.greeks.theta` | Yes (indicative feed) |
| Last Trade Price | `snapshot.latest_trade.price` | Yes (indicative feed) |

**Important nuance -- Open Interest:**
Open Interest is NOT in the `OptionsSnapshot` from the market data API. It is on the `OptionContract` object returned by `TradingClient.get_option_contracts()`. The existing `BrokerClient.get_options_contracts()` already fetches this and the existing `Contract` dataclass already stores `oi` from `contract.open_interest`. This is already working in the codebase.

**OptionChainRequest parameters (verified):**
```python
from alpaca.data.requests import OptionChainRequest

request = OptionChainRequest(
    underlying_symbol="AAPL",
    type=ContractType.CALL,              # or PUT
    expiration_date_gte="2026-03-18",    # min expiry
    expiration_date_lte="2026-04-18",    # max expiry
    strike_price_gte=150.0,              # min strike
    strike_price_lte=200.0,              # max strike
)
chain = option_client.get_option_chain(request)
# Returns: Dict[str, OptionsSnapshot]
```

**Integration approach:**
The current `BrokerClient` already has `get_options_contracts()` (trading API, returns contracts with OI) and `get_option_snapshot()` (market data API, returns snapshots with bid/ask/greeks/IV). The existing `Contract.from_contract_snapshot()` already joins these two data sources. For the screener, the same pattern applies:

1. Use `get_options_contracts()` for the contract list (includes OI)
2. Use `get_option_snapshot()` for bid/ask/greeks/IV
3. Join them via the existing `Contract.from_contract_snapshot()` constructor
4. Filter on OI minimum, bid/ask spread ratio, delta range

**New filter functions needed in pipeline (using existing data model):**
- `filter_option_oi(contract, min_oi)` -- already modeled in `config/params.py` as `OPEN_INTEREST_MIN = 100`
- `filter_option_spread(contract, max_spread_pct)` -- `(ask - bid) / ask * 100 < threshold`

**Confidence: HIGH** -- All classes already exist in the installed alpaca-py 0.43.2. The project already uses the exact same APIs for put/call execution. Free tier indicative feed confirmed to include greeks and IV.

### Free Tier Data Quality Note

The Alpaca free tier uses the "indicative" options feed rather than the "OPRA" feed. The indicative feed provides estimated option values rather than actual exchange quotes. For screening purposes (filtering, not execution), this is adequate. The existing `BrokerClient` already defaults to the free indicative feed.

## New Capability 4: Covered Call Screening CLI

### Approach: Typer CLI + existing Rich display (no new dependencies)

**Recommendation:** Add a `run-call-screener` console script using the same patterns as the existing `run-screener` CLI. Typer and Rich are already installed and used.

**CLI registration in pyproject.toml:**
```toml
[project.scripts]
run-strategy = "scripts.run_strategy:main"
run-screener = "scripts.run_screener:main"
run-call-screener = "scripts.run_call_screener:main"  # NEW
```

**Integration points:**
- `scripts/run_call_screener.py` -- New entry point (follows `run_screener.py` pattern)
- `screener/call_pipeline.py` -- New pipeline for covered call screening (uses `run_pipeline()` survivors as input, then adds call-specific option chain analysis)
- `screener/display.py` -- Extend existing Rich table display for call screening results
- `screener/config_loader.py` -- Extend `ScreenerConfig` with call-specific thresholds

**Covered call screening flow:**
1. Run the existing put screener pipeline to get wheel-suitable stocks (or take user-provided symbol list)
2. For each candidate: fetch call option chain via `get_option_chain()`
3. Filter calls by: DTE range, delta range, OI minimum, bid/ask spread maximum
4. Score by: premium yield, delta, DTE (similar to existing `score_options()`)
5. Display results with Rich table

**Existing code reuse:**
- `core/strategy.py::filter_options()` already filters by delta range, OI, yield
- `core/strategy.py::score_options()` already scores by delta, DTE, bid/strike
- `core/broker_client.py::get_options_contracts()` already fetches contracts
- `screener/display.py` already renders Rich tables with color-coded scores
- The existing scoring formula `(1 - |delta|) * (250 / (DTE + 5)) * (bid / strike)` works for calls too

**Confidence: HIGH** -- Pure application layer, no new dependencies, follows established patterns.

## What NOT to Add

| Library/Service | Why Avoid | Use Instead |
|-----------------|-----------|-------------|
| scipy (Black-Scholes IV) | Adds a heavy dependency (50MB+) for computing IV from option prices; Alpaca already provides IV in snapshots | `OptionsSnapshot.implied_volatility` from Alpaca |
| yfinance (for HV data) | Unofficial Yahoo scraper, breaks regularly, redundant since Alpaca bars already provide close prices | Existing Alpaca daily bars via `fetch_daily_bars()` |
| tradingview-ta | Web scraping, fragile, no IV Rank data anyway | Compute HV Rank from existing bar data |
| Barchart API | Paid for IV Rank data; free tier is too limited | HV Percentile Rank computed locally |
| ORATS / IVolatility | Paid APIs for historical IV data | HV Percentile Rank as proxy |
| Alpha Vantage | 25 calls/day free tier too restrictive; Finnhub already covers earnings | Finnhub earnings_calendar endpoint |
| ratelimit (PyPI) | Last release 2019, unnecessary complexity | Existing manual `_throttle()` in FinnhubClient (already working) |
| Any new earnings API | Would add new API key, new client, new rate limit management | Finnhub earnings_calendar (already integrated) |

**Confidence: HIGH** -- Verified that alternatives are either paid, fragile, or redundant with existing stack.

## Installation

```bash
# No new packages needed!
# All capabilities use the existing installed stack.

# If starting fresh:
uv pip install -e .
# This installs: alpaca-py, finnhub-python, ta, pydantic, rich, typer, numpy, pandas, pyyaml
```

## Version Compatibility Matrix

| Package | Version | Used For (v1.1) | Compatibility Notes |
|---------|---------|-----------------|---------------------|
| alpaca-py | 0.43.2 | Option chain, snapshots, OI, greeks, IV | `OptionChainRequest` class verified available |
| finnhub-python | 2.4.27 | Earnings calendar | `earnings_calendar()` method verified in SDK |
| numpy | 2.4.2 | HV Rank percentile computation | Only stdlib math needed (`np.std`, `np.log`, `np.sqrt`) |
| pandas | 3.0.1 | Daily bar DataFrames | Already used for bar data in `market_data.py` |
| pydantic | 2.12.5 | Config model extensions | Add call screening fields to `ScreenerConfig` |
| rich | 14.3.3 | Call screener output table | Extend existing `display.py` patterns |
| typer | 0.24.1 | `run-call-screener` CLI | Follow existing `run_screener.py` pattern |
| ta | 0.11.0 | RSI, SMA indicators | No changes needed for v1.1 |
| PyYAML | 6.0.3 | Config loading | No changes needed for v1.1 |

## API Endpoint Summary for v1.1

| Capability | API/Endpoint | Rate Limit | Cost |
|-----------|-------------|------------|------|
| HV Rank | None (local computation) | N/A | Free |
| Earnings Calendar | Finnhub `earnings_calendar` | 60/min (shared with other Finnhub calls) | Free tier |
| Option Chain (OI) | Alpaca `get_option_contracts` | No explicit limit | Free tier |
| Option Chain (bid/ask/IV/greeks) | Alpaca `get_option_snapshot` or `get_option_chain` | No explicit limit | Free tier (indicative feed) |
| Covered Call Screening | Alpaca option chain + scoring | No explicit limit | Free tier |

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| No new dependencies needed | HIGH | All packages verified installed, all API methods verified in SDK docs |
| HV Rank as IV Rank proxy | HIGH | Standard approach, uses only numpy on existing data |
| Finnhub earnings_calendar | HIGH | SDK method signature verified from GitHub README, free tier confirmed |
| Alpaca option chain data | HIGH | OptionsSnapshot model fields verified from SDK docs, free tier includes indicative feed |
| Covered call CLI pattern | HIGH | Follows identical pattern to existing run-screener CLI |
| Free tier indicative feed quality | MEDIUM | Indicative feed provides estimated values, not exchange quotes; adequate for screening but may differ from real-time prices |

## Sources

- [Alpaca-py SDK Options Data Requests](https://alpaca.markets/sdks/python/api_reference/data/option/requests.html) -- OptionChainRequest parameters
- [Alpaca-py SDK Data Models](https://alpaca.markets/sdks/python/api_reference/data/models.html) -- OptionsSnapshot, Quote, Trade, OptionsGreeks fields
- [Alpaca-py SDK Options Historical Data](https://alpaca.markets/sdks/python/api_reference/data/option/historical.html) -- get_option_chain, get_option_snapshot methods
- [Alpaca Market Data API Overview](https://docs.alpaca.markets/docs/about-market-data-api) -- Free tier indicative vs OPRA feed
- [Alpaca Option Chain Endpoint](https://docs.alpaca.markets/reference/optionchain) -- REST endpoint parameters
- [Finnhub Earnings Calendar Docs](https://finnhub.io/docs/api/earnings-calendar) -- Response schema, free tier availability
- [Finnhub Python SDK GitHub](https://github.com/Finnhub-Stock-API/finnhub-python) -- earnings_calendar() method signature
- [finnhub-python on PyPI](https://pypi.org/project/finnhub-python/) -- Version 2.4.27
- [alpaca-py on PyPI](https://pypi.org/project/alpaca-py/) -- Version 0.43.2
- Installed packages verification via `pip list` in project venv

---
*Stack research for: Wheeely v1.1 Screener Fix + Covered Call Screening*
*Researched: 2026-03-11*

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

# Domain Pitfalls

**Domain:** Options Wheel Screener — Screener Fix + Covered Call Screening (v1.1)
**Researched:** 2026-03-11
**Overall confidence:** HIGH (based on code analysis, Finnhub API documentation, community reports, and domain expertise)

## Critical Pitfalls

### Pitfall 1: Finnhub `totalDebtToEquity` Is a Percentage, Not a Ratio — The Root Cause of Zero Results

**What goes wrong:** The current screener has `debt_equity_max: 1.0` in moderate preset, meaning "D/E ratio at most 1.0x". But Finnhub's `totalDebtToEquity` metric returns values as **percentages** (e.g., 150.0 means 1.5x D/E), not decimal ratios. A stock with a healthy 0.5x D/E is reported by Finnhub as `50.0`. The filter sees `50.0 > 1.0` and eliminates it. Every single stock with any debt at all gets eliminated.

**Why it happens:** Finnhub's API documentation does not specify the unit format of its metrics. The `company_basic_financials` endpoint returns 117+ metric keys with no format documentation. The Robot Wealth analysis of Finnhub data shows `totalDebtToEquity` values like 2.3881, 1.9903, 1.7309 for Apple annual data — but these may be from the `series` (historical annual) response, which uses a different format than the `metric` (current snapshot) response. The current snapshot likely returns percentage-formatted values (e.g., AAPL at ~170.0 rather than 1.70), based on the fact that all 202 Stage 1 survivors were eliminated by the D/E filter.

**Evidence from the codebase:**
- `config_loader.py` line 26: `debt_equity_max: float = 1.0` — expects ratio format
- `finnhub_client.py` lines 23-27: fallback chain tries `totalDebtToEquity`, `totalDebtToEquityQuarterly`, `totalDebtToEquityAnnual`
- `pipeline.py` line 599: `stock.debt_equity = extract_metric(metrics, "debt_equity")` — raw value, no conversion
- `pipeline.py` line 287: `if stock.debt_equity > max_de:` — compares raw Finnhub value against 1.0

**Consequences:** ALL 202 Stage 1 survivors eliminated. Zero screening results. Complete pipeline failure.

**Prevention:**
1. **Diagnostic first:** Before fixing, add a debug mode that logs the raw `totalDebtToEquity` value for 5 well-known stocks (AAPL, MSFT, GOOGL, JNJ, KO). If AAPL returns ~170.0, the value is percentage-formatted. If it returns ~1.70, it is ratio-formatted.
2. **Normalization layer:** Add a `normalize_metric()` function in `finnhub_client.py` that converts Finnhub values to a consistent format. For D/E: if value > 10, divide by 100 (heuristic: no sane D/E ratio exceeds 10x except for financials, which should be sector-excluded anyway).
3. **Alternative fix:** Change the threshold to match Finnhub's format — set `debt_equity_max: 100.0` (representing 100% or 1.0x). But this is fragile; normalization is better.
4. **Test with real data:** Write a one-off script that fetches Finnhub metrics for 10 known stocks and asserts the D/E values match publicly available figures (e.g., AAPL D/E ~1.7x from MacroTrends).

**Detection:** Run screener with `--log-level DEBUG` and add logging to `extract_metric()` showing raw values. If all D/E values are >10, the format is percentage.

**Phase:** Must be Phase 1 (Debug/Fix). This is the blocking bug.

**Confidence:** HIGH — the code path is clear, the threshold of 1.0 vs percentage-format values is the most parsimonious explanation for "all 202 eliminated by debt_equity".

---

### Pitfall 2: None/Null Values Treated as Filter Failure, Silently Eliminating Good Stocks

**What goes wrong:** When Finnhub returns `null` for a metric (common for smaller companies, companies with unusual corporate structures, or companies that haven't filed recent financials), the `extract_metric()` function returns `None`. The filter functions treat `None` as failure:

```python
# pipeline.py line 278-285
if stock.debt_equity is None:
    return FilterResult(
        filter_name="debt_equity",
        passed=False,
        ...
        reason="Debt/equity data unavailable",
    )
```

This means stocks like Berkshire Hathaway (no D/E because of its structure), many REITs, and newer companies get eliminated silently.

**Why it happens:** The v1.0 design assumed Finnhub would have complete data for any stock that passes Stage 1. In practice, Finnhub's free tier has significant coverage gaps:
- Small/mid-cap stocks frequently lack `totalDebtToEquity` data
- Companies that recently IPO'd may not have financials populated yet
- Some valid metric keys are missing for specific stocks — only one of the three fallback keys may exist, and sometimes none do
- The fallback chain `["totalDebtToEquity", "totalDebtToEquityQuarterly", "totalDebtToEquityAnnual"]` may all return `None`

**Consequences:** Stocks with missing data are eliminated alongside stocks with genuinely bad fundamentals. The filter report shows "Debt/equity data unavailable" but this is indistinguishable from "stock was filtered" in the elimination summary. This could silently remove 30-50% of stocks that would otherwise qualify.

**Prevention:**
1. **Pass-on-None strategy:** For non-critical metrics, treat `None` as "not enough data to disqualify" rather than "disqualified". Change `passed=False` to `passed=True` for `None` values, or make this configurable per-filter.
2. **Soft vs. hard filters:** Categorize filters as "hard" (must have data, e.g., market cap) vs. "soft" (skip if no data, e.g., D/E for non-financial companies). Make this configurable in the YAML preset.
3. **Data completeness logging:** Log the percentage of Stage 1 survivors that have each metric available. If <50% have D/E data, the filter is effectively broken.
4. **Scoring penalty instead of elimination:** Instead of eliminating stocks with missing D/E, penalize their score. A stock with unknown D/E gets a lower fundamental sub-score but still enters the results.

**Detection:** Add a counter in `run_stage_2_filters` tracking how many stocks fail each filter due to `None` vs. due to threshold violation. If >50% of failures for a filter are `None`-based, the filter has a data quality problem.

**Phase:** Phase 1 (Debug/Fix). This compounds with Pitfall 1 to produce the zero-result bug.

**Confidence:** HIGH — the code explicitly returns `passed=False` on `None`.

---

### Pitfall 3: IV Rank Requires 252 Trading Days of IV History, Not Just Current IV

**What goes wrong:** IV Rank is defined as `(Current IV - 52-week Low IV) / (52-week High IV - 52-week Low IV)`. This requires knowing the high and low of IV over the past year. The common mistake is computing current IV from today's options chain and calling it "IV Rank" — but that is just IV, not IV Rank.

**Why it happens:** Implied volatility is readily available from any options chain snapshot. But the 52-week high and low require either:
- Storing daily IV snapshots for a year (data infrastructure the project doesn't have)
- Using a paid API that provides IV Rank directly (ORATS, Barchart, MarketChameleon)
- Approximating from historical volatility (HV), which is what the project plans to do

**Consequences:**
- If you display "IV Rank" but it's actually just current IV, users make incorrect trading decisions (selling premium when IV is actually low relative to history)
- If you use HV as a proxy, it's directionally useful but systematically different from true IV Rank — HV does not capture event risk (earnings, FDA decisions) that inflates IV
- HV Rank (using `(Current HV - 52-week Low HV) / (52-week High HV - 52-week Low HV)`) is a reasonable proxy but must be clearly labeled as such

**Prevention:**
1. **Label honestly:** Call it "HV Rank" or "Volatility Rank (HV-based)", never "IV Rank", unless using actual IV data.
2. **Leverage existing code:** The pipeline already computes `hv_30` via `compute_historical_volatility()`. Extend this to compute 252-day rolling HV, then derive HV Rank from the series.
3. **Data requirement:** Need at least 252+30 = 282 trading days of daily bars to compute a meaningful HV Rank. The pipeline already fetches 250 bars (`num_bars=250`). Increase to 300.
4. **VIX Fix alternative:** The Williams VIX Fix indicator (highest close over 22 days minus current low, divided by highest close) is another free, price-derived volatility proxy used by TradingView options screeners. It reacts faster to volatility spikes than HV.
5. **Beware single-spike distortion:** IV Rank and HV Rank are both distorted by a single volatility spike (e.g., one day during a crash). IV Percentile (percentage of days IV was lower than today) is more robust. Consider computing both.

**Detection:** Compare your HV Rank output against Barchart's free IV Rank page for 10 stocks. If correlation is <0.5, the proxy is too loose.

**Phase:** Phase 2 or 3 (IV Rank/Earnings features). Design the data structure early so it can be upgraded to real IV data later.

**Confidence:** HIGH — this is well-documented in options trading literature.

---

### Pitfall 4: `avg_volume_min: 2,000,000` Is Far Too Restrictive

**What goes wrong:** The current moderate preset requires average daily volume of 2 million shares. According to the filter breakdown, this eliminates 10,758 stocks (85% of the universe). Combined with the D/E bug, this is the second major filter kill.

**Why it happens:** 2M average daily volume sounds reasonable for liquid large-caps, but the median US stock has ~200K-500K daily volume. Only ~500-800 US stocks consistently trade above 2M shares/day.

**Evidence from the codebase:**
- `config_loader.py` line 52: `avg_volume_min: int = 2_000_000`
- All three presets use `avg_volume_min: 2000000` — conservative, moderate, and aggressive all have the same value
- The "aggressive" preset should absolutely have a lower volume threshold

**Consequences:** The screener is too restrictive for its stated purpose. Many wheel-suitable stocks (mid-caps with good options liquidity) are eliminated. The aggressive preset is not actually aggressive on this dimension.

**Prevention:**
1. **Differentiate presets:** Conservative: 2M, Moderate: 500K, Aggressive: 200K
2. **Use dollar volume instead:** `avg_volume * price` as a threshold is more meaningful. A $200 stock with 100K volume has $20M daily dollar volume (very liquid), but gets eliminated by a 500K share-volume filter.
3. **Options liquidity matters more:** For wheel strategy, what matters is options open interest and bid/ask spread, not underlying stock volume per se. A stock with 300K share volume but 5,000 OI on nearby puts is more suitable than one with 3M share volume but 50 OI on puts.
4. **Lower the default, add options OI filter:** Reduce `avg_volume_min` to 500K and add a new `min_open_interest` filter on the options chain (which is planned for v1.1 anyway).

**Detection:** Check how many Stage 1 survivors exist at different volume thresholds (500K, 1M, 2M, 5M). If 2M drops the survivor count by >50% vs 500K, it's too restrictive.

**Phase:** Phase 1 (Debug/Fix) — preset threshold adjustment.

**Confidence:** HIGH — the filter breakdown explicitly shows 10,758 stocks eliminated.

---

### Pitfall 5: Earnings Calendar Data Is Unreliable on Free APIs

**What goes wrong:** Free earnings calendar APIs (including Finnhub) have documented accuracy problems. Dates may be wrong by days or weeks, especially for smaller companies. Companies change their earnings dates, and free APIs may not update promptly. Confirmed issue: Finnhub GitHub Issue #528 reports CAN stock showing November 14 instead of the correct November 28.

**Why it happens:** Earnings dates come from company IR announcements, SEC filings, and third-party estimates. Free APIs typically:
- Use estimated dates early (which shift)
- May not update when companies reschedule
- Have worse coverage for small/mid-caps
- May confuse fiscal quarter end dates with earnings announcement dates

**Consequences:**
- Selling a put 7 days before earnings (thinking earnings is 21 days away) exposes you to massive gap risk
- Missing an earnings date means you could hold through a volatile event unknowingly
- False "safe" signals from stale calendar data are worse than no calendar at all

**Prevention:**
1. **Buffer zone:** Use a wider exclusion window (e.g., 14 days before earnings instead of 7) to account for date inaccuracies.
2. **Multiple source verification:** Cross-check Finnhub earnings date with at least one other source. Finnhub + Yahoo Finance (via `yfinance` library which provides `.info['earningsDate']`) gives a second data point.
3. **Fail-safe on missing data:** If no earnings date is found, do NOT assume "no upcoming earnings." Instead, flag as "unknown earnings date — proceed with caution" and penalize the score rather than pass.
4. **Freshness indicator:** Log when the earnings date was last fetched. If the cache is >7 days old, re-fetch before making decisions.
5. **Prefer Finnhub's own endpoint:** Finnhub has a dedicated earnings calendar endpoint (`/calendar/earnings`) — use it rather than trying to parse dates from other sources. It returns `date`, `epsActual`, `epsEstimate`, `hour` (bmo/amc/dmh), and `symbol`.

**Detection:** For any stock where you plan to sell options, manually verify the next earnings date against the company's IR page. If >2 dates out of 10 are wrong, add the buffer zone.

**Phase:** Phase 2 or 3 (earnings calendar feature).

**Confidence:** MEDIUM — Finnhub earnings dates are directionally correct for large-caps, but the documented inaccuracy issues and lack of official Finnhub response to Issue #528 lower confidence for small/mid-caps.

---

### Pitfall 6: Options Chain Data Fetching Will Hit Rate Limits at Scale

**What goes wrong:** Fetching options chain data (OI, bid/ask spread) for all Stage 2 survivors requires per-symbol API calls to Alpaca's option chain endpoint. The endpoint has a rate limit of 200 requests/minute (paper) and returns up to 100 contracts per request. If 50 stocks survive Stage 2 and each has 200+ option contracts, you need multiple paginated requests per symbol.

**Why it happens:** The existing `BrokerClient` already paginates option contract fetches (1000 per page) and batches snapshots (100 per batch) for the strategy execution flow. But screening is different — you need chain data for many more symbols than the strategy ever handles (which only processes the curated symbol list).

**Evidence from the codebase:**
- `core/broker_client.py`: existing pagination for option contracts (1000/page, 100/batch snapshots)
- Alpaca rate limit: 200 requests/minute for paper accounts
- Option chain endpoint: 100 contract symbols per request

**Consequences:**
- Screening 50 stocks' option chains could take 5+ minutes
- Combined with Finnhub rate limiting (already 3-4 minutes for Stage 2), total screening time could exceed 10 minutes
- Rate limit errors could cause partial data, leading to incorrect OI/spread filtering

**Prevention:**
1. **Filter before fetching chains:** Only fetch option chain data for stocks that pass all other filters. This should reduce the set to 30-50 stocks.
2. **Fetch only relevant strikes:** Use the option chain endpoint with strike price filters (e.g., strikes within 10% of current price) rather than the full chain.
3. **Fetch only relevant expirations:** Filter to 30-45 DTE expirations only — don't fetch the entire expiration calendar.
4. **Cache aggressively:** Option chain data changes intraday but not dramatically. Cache for 1 hour during screening.
5. **Batch where possible:** Use Alpaca's multi-symbol option snapshot endpoint if available, or batch requests with appropriate rate limiting.

**Detection:** Time the option chain fetch step separately and log request counts. If >100 requests needed, optimize filtering.

**Phase:** Phase 3 (Options chain OI/spread filtering).

**Confidence:** MEDIUM — the exact rate limit behavior depends on Alpaca plan tier and whether paper/live differs.

## Moderate Pitfalls

### Pitfall 7: HV-Based Volatility Proxy Diverges from IV Around Earnings and Events

**What goes wrong:** Historical volatility (HV) measures past price movement. Implied volatility (IV) measures expected future movement priced into options. Around earnings, FDA decisions, and other binary events, IV spikes dramatically while HV stays flat (the event hasn't happened yet). An HV-based screener will miss these IV-rich opportunities — which are exactly the events wheel traders want to capture premium from.

**Prevention:**
1. Accept the limitation and document it: "HV Rank identifies structurally volatile stocks, not event-driven IV spikes."
2. Combine with earnings calendar: if earnings are 2-4 weeks away AND HV Rank is moderate, flag as "potential IV opportunity."
3. Consider augmenting with VIX correlation: stocks with high beta to VIX tend to have IV>HV divergence.

**Phase:** Phase 2 (IV Rank feature design).

### Pitfall 8: Covered Call Screener Has Different Criteria Than Put Screener

**What goes wrong:** The put screener finds stocks you want to own at a lower price. The covered call screener finds optimal calls to sell on stocks you already own. Reusing the same filters for both produces poor results:
- Put screener wants: low RSI (stock dipping), high HV (rich premiums), above SMA200 (uptrend)
- Call screener wants: high RSI (momentum to sell into), moderate HV (not too volatile to get called away cheaply), stock near resistance levels

**Prevention:**
1. **Separate filter configurations:** Add a `call_screener` section to the YAML config with its own thresholds, distinct from the put screener.
2. **Context-aware screening:** The call screener already knows which stocks you hold (from `state_manager.update_state()`). It only needs to screen the options chain for those specific stocks, not the entire universe.
3. **Different scoring formula:** For calls, score based on: (a) premium yield at target delta, (b) distance from cost basis (don't sell calls below your entry), (c) days since assignment (favor fresher positions).
4. **Position-aware strike selection:** The call strike must be at or above the cost basis to avoid locking in a loss. This requires passing the entry price from `state_manager` to the screener.

**Phase:** Phase 4 (Covered call screening).

### Pitfall 9: Bid/Ask Spread Filter on Illiquid Options Eliminates Too Aggressively

**What goes wrong:** Setting a strict bid/ask spread filter (e.g., spread < $0.30 or spread < 5% of mid) on options eliminates most small/mid-cap stocks. Options on stocks with 200K-1M daily volume often have $0.50-$1.00 spreads, especially on further-out expirations.

**Prevention:**
1. **Use relative spread:** Filter on `spread / mid_price` percentage rather than absolute dollar amount. A $0.50 spread on a $5.00 option (10%) is worse than a $1.00 spread on a $15.00 option (6.7%).
2. **Only check target strikes:** Don't check the spread on every strike in the chain. Check the 2-3 strikes nearest to your target delta.
3. **Differentiate by DTE:** Near-term options (7-14 DTE) naturally have tighter spreads. 30-45 DTE options may have wider spreads during low-activity periods.
4. **Use the threshold from the strategy params:** The existing `config/params.py` already has bid-based scoring logic. Align the screener's spread threshold with the strategy's actual execution requirements.
5. **Recommended threshold:** Spread < 10% of mid price for moderate preset, < 5% for conservative, < 15% for aggressive.

**Phase:** Phase 3 (Options chain filtering).

### Pitfall 10: Finnhub `marketCapitalization` Is in Millions, Not Dollars

**What goes wrong:** The code already handles this (line 596: `raw_market_cap * 1_000_000`), but the same pattern might not be applied to new metrics. Finnhub returns some values in millions, some as raw numbers, some as percentages — with no consistent convention.

**Prevention:**
1. **Document every Finnhub metric's unit:** Create a mapping table in `finnhub_client.py` that specifies the unit for each metric the system uses.
2. **Add unit normalization alongside fallback chains:** Extend `METRIC_FALLBACK_CHAINS` to also specify the expected unit conversion for each key.
3. **Test with known values:** For any new metric, fetch it for 3 well-known stocks and verify against a reference source (MacroTrends, Yahoo Finance).

**Phase:** Any phase adding new Finnhub metrics.

## Minor Pitfalls

### Pitfall 11: Preset Differentiation Is Cosmetic — Technicals Are Identical

**What goes wrong:** All three presets (conservative, moderate, aggressive) have identical technical thresholds: `price_min: 10`, `price_max: 50`, `avg_volume_min: 2000000`, `rsi_max: 60`, `above_sma200: true`. Only fundamentals differ. This means the presets only differentiate on fundamental strictness, not trading aggressiveness.

**Prevention:**
- Conservative: `price_max: 100`, `avg_volume_min: 2000000`, `rsi_max: 50`, `above_sma200: true`
- Moderate: `price_max: 75`, `avg_volume_min: 500000`, `rsi_max: 65`, `above_sma200: true`
- Aggressive: `price_max: 150`, `avg_volume_min: 200000`, `rsi_max: 75`, `above_sma200: false`

**Phase:** Phase 1 (preset update).

### Pitfall 12: Sector Exclude Lists Need Finnhub's Exact Industry Names

**What goes wrong:** Finnhub uses `finnhubIndustry` field (not standard GICS sectors). The values are specific to Finnhub's taxonomy: e.g., "Technology" not "Information Technology", "Financial Services" not "Financials". If the YAML config uses GICS names but Finnhub returns Finnhub-specific names, the sector filter silently fails.

**Prevention:**
1. Document the exact `finnhubIndustry` values in the YAML config comments.
2. Fetch all unique `finnhubIndustry` values from a sample of stocks and list them in the presets as reference.
3. Use case-insensitive matching (already implemented in `filter_sector()`).
4. Consider fuzzy matching or a mapping table from common sector names to Finnhub's taxonomy.

**Phase:** Phase 1 (preset update) or Phase 2 (sector lists).

### Pitfall 13: Historical Bar Count Off-By-One for HV Computation

**What goes wrong:** `compute_historical_volatility()` requires `window+1` prices to get `window` returns (line 506: `if len(bars_df) < window + 1`). For HV Rank, you need 252 trading days of HV values, each requiring 30 returns, meaning you need 282 bars minimum. The pipeline currently fetches 250 bars (`num_bars=250`). This is insufficient for HV Rank.

**Prevention:** Increase `num_bars` to 300 or 320 to provide margin for weekends, holidays, and the HV Rank lookback window.

**Phase:** Phase 2 (HV Rank computation).

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Debug filter pipeline | Pitfall 1 (D/E format) + Pitfall 2 (None handling) | Diagnostic logging first, then fix normalization |
| Fix preset thresholds | Pitfall 4 (volume too high) + Pitfall 11 (identical technicals) | Research actual distribution of values before setting thresholds |
| Add HV Rank | Pitfall 3 (HV != IV Rank) + Pitfall 13 (bar count) | Label as "HV Rank", increase bar count to 300+ |
| Add earnings calendar | Pitfall 5 (date accuracy) | Use 14-day buffer, cross-reference sources |
| Add options OI/spread | Pitfall 6 (rate limits) + Pitfall 9 (spread too strict) | Filter before fetching, use relative spread |
| Covered call screening | Pitfall 8 (different criteria) | Separate config section, position-aware scoring |
| Sector configuration | Pitfall 12 (Finnhub taxonomy) | Document exact Finnhub industry names |

## Sources

- [Finnhub Basic Financials API](https://finnhub.io/docs/api/company-basic-financials) — metric key documentation
- [Finnhub Earnings Calendar API](https://finnhub.io/docs/api/earnings-calendar) — earnings endpoint documentation
- [Finnhub Earnings Calendar Accuracy Issue #528](https://github.com/finnhubio/Finnhub-API/issues/528) — documented date inaccuracy
- [Finnhub Metric Data Quality Issue #337](https://github.com/finnhubio/Finnhub-API/issues/337) — metric value inconsistency
- [Robot Wealth: Exploring the Finnhub API](https://robotwealth.com/finnhub-api/) — metric format analysis showing D/E values
- [Alpaca Option Chain API](https://docs.alpaca.markets/reference/optionchain) — rate limits and response structure
- [Alpaca Rate Limits](https://alpaca.markets/support/usage-limit-api-calls) — 200 req/min paper accounts
- [Days to Expiry: Best Stocks for Wheel Strategy](https://www.daystoexpiry.com/blog/best-stocks-wheel-strategy) — screening criteria recommendations
- [Barchart: IV Rank vs IV Percentile](https://www.barchart.com/education/iv_rank_vs_iv_percentile) — IV Rank computation methodology
- [Charles Schwab: Using IV Percentiles](https://www.schwab.com/learn/story/using-implied-volatility-percentiles) — IV Percentile vs IV Rank
- [TradingView: IV Rank VIXFix HV Proxy](https://www.tradingview.com/script/HyEYHf6d-IV-Rank-tasty-style-VIXFix-HV-Proxy/) — HV-based IV Rank proxy approach
- [Apple D/E from MacroTrends](https://www.macrotrends.net/stocks/charts/AAPL/apple/debt-equity-ratio) — reference D/E values for verification

---
*Pitfalls research for: Screener Fix + Covered Call Screening (v1.1)*
*Researched: 2026-03-11*