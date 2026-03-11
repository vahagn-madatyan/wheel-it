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
