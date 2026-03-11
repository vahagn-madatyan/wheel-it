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
