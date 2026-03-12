# Phase 3: Screening Pipeline - Research

**Researched:** 2026-03-08
**Domain:** Stock screening pipeline -- Alpaca universe fetching, filter logic, scoring, optionable checking, IV/volatility data
**Confidence:** HIGH

## Summary

This phase builds the core screening pipeline that takes ~8,000+ Alpaca-tradable US equities through a 3-stage filter (Alpaca-cheap -> Finnhub-expensive -> Score) and returns scored, ranked results. The key infrastructure already exists from Phases 1-2: `ScreenerConfig` for filter thresholds, `ScreenedStock` dataclass with progressive population and `FilterResult` tracking, `FinnhubClient` with rate limiting, and `market_data.py` for bar fetching + indicator computation.

The primary research findings center on four areas: (1) Alpaca's `get_all_assets()` with `GetAssetsRequest(attributes="options_enabled")` provides a single-call way to identify optionable stocks -- no per-symbol API calls needed for FILT-09. (2) Alpaca's `OptionsSnapshot` model includes `implied_volatility` directly, but fetching it for 200+ stocks during screening would cost 200+ API calls and is better suited as a SCOR-01 enhancement. The recommended approach for v1 scoring is historical volatility (HV) computed from the daily bars already fetched in Stage 1. (3) Finnhub `basic_financials` returns `beta` in its metrics dict, which can serve as a secondary volatility signal. (4) The pipeline should make exactly 2 Alpaca asset calls upfront (all tradable + options_enabled), then batch bar fetching, then sequential Finnhub calls only for survivors of Stage 1.

**Primary recommendation:** Build a 3-stage pipeline in `screener/pipeline.py` that uses two upfront Alpaca asset API calls to establish universe + optionable set, batch-fetches bars and computes indicators (including HV) for cheap filtering, then calls Finnhub sequentially for expensive filtering, and finally scores all survivors. Use historical volatility (annualized std dev of log returns over 30 days) as the volatility proxy for scoring.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use ALL Alpaca-tradable US equities as the starting universe (~8,000+ symbols)
- Query Alpaca's asset API for active, tradable stocks -- single fast call
- Merge existing `config/symbol_list.txt` symbols into the universe so currently-traded symbols are always re-evaluated
- No curated seed list -- maximize discovery of new wheel candidates
- 3-stage pipeline: Alpaca -> Finnhub -> Score
  - Stage 1 (Alpaca/cheap): Price range, average volume, RSI(14), SMA(200), above_sma200 -- all from already-fetched bar data
  - Stage 2 (Finnhub/expensive): Market cap, debt/equity, net margin, sales growth, sector, optionable -- requires API calls
  - Stage 3: Score all survivors, sort descending
- Short-circuit between stages: run all filters within a stage, skip subsequent stages if any filter failed
- Finnhub calls only happen for stocks that pass ALL cheap Alpaca filters
- Capital efficiency first in scoring -- prioritize stocks where tied-up capital generates the most premium
- Three scoring components: premium yield potential (via volatility proxy), capital efficiency, fundamental strength
- Capital efficiency weighted highest
- Normalized 0-100 scale -- each component normalized to 0-1, weighted, scaled to 0-100
- Return all passing stocks scored and sorted (no top-N limit)
- Sector filtering: Case-insensitive exact match against Finnhub's finnhubIndustry values
- Empty include list = all sectors allowed
- Missing/null sector data from Finnhub = fail the sector filter
- Return ALL ScreenedStock objects (both passing and eliminated) with FilterResults populated
- Phase 4 needs eliminated stocks for per-filter elimination count reporting
- Callers use passed_all_filters property to separate winners from losers

### Claude's Discretion
- Exact scoring formula weights (capital efficiency > volatility > fundamentals, but exact ratios TBD)
- Historical volatility computation details (if used as fallback)
- Internal module structure (single pipeline.py vs split by stage)
- How to check optionable status via Alpaca API
- Batch size for Alpaca bar fetching across 8,000+ symbols

### Deferred Ideas (OUT OF SCOPE)
- Finnhub response caching with TTL (v2 requirement PERF-01)
- Per-symbol verbose filter decisions (v2 requirement PERF-02)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FILT-01 | Filter stocks by market cap minimum using Finnhub data | Stage 2 filter; FinnhubClient.company_profile() returns `marketCapitalization` (in millions); compare against ScreenerConfig.fundamentals.market_cap_min |
| FILT-02 | Filter stocks by debt/equity ratio maximum using Finnhub data | Stage 2 filter; FinnhubClient.company_metrics() with extract_metric(metrics, "debt_equity") fallback chain; compare against ScreenerConfig.fundamentals.debt_equity_max |
| FILT-03 | Filter stocks by net margin minimum using Finnhub data | Stage 2 filter; extract_metric(metrics, "net_margin") fallback chain; compare against ScreenerConfig.fundamentals.net_margin_min |
| FILT-04 | Filter stocks by quarterly sales growth minimum using Finnhub data | Stage 2 filter; extract_metric(metrics, "sales_growth") fallback chain; compare against ScreenerConfig.fundamentals.sales_growth_min |
| FILT-05 | Filter stocks by price range using Alpaca market data | Stage 1 filter; price from compute_indicators()["price"]; compare against ScreenerConfig.technicals.price_min/price_max |
| FILT-06 | Filter stocks by minimum average daily volume using Alpaca market data | Stage 1 filter; avg_volume from compute_indicators()["avg_volume"]; compare against ScreenerConfig.technicals.avg_volume_min |
| FILT-07 | Filter stocks by RSI(14) maximum using Alpaca bars + ta library | Stage 1 filter; rsi_14 from compute_indicators()["rsi_14"]; None = fail; compare against ScreenerConfig.technicals.rsi_max |
| FILT-08 | Filter stocks where price is above SMA(200) using Alpaca bars | Stage 1 filter; above_sma200 from compute_indicators()["above_sma200"]; None = fail; compare against ScreenerConfig.technicals.above_sma200 |
| FILT-09 | Filter stocks that are optionable using Alpaca options data | Resolved via Alpaca GetAssetsRequest(attributes="options_enabled") single upfront call; check symbol membership in optionable_set; runs in Stage 2 (after cheap filters) |
| FILT-10 | Filter stocks by GICS sector/industry using Finnhub profile data | Stage 2 filter; FinnhubClient.company_profile()["finnhubIndustry"]; case-insensitive match against SectorsConfig include/exclude lists; missing = fail |
| SCOR-01 | Score each passing stock for wheel suitability based on premium yield, capital efficiency, fundamental strength | Three-component weighted score using HV (from bars), capital efficiency (100/price proxy), and fundamental composite; see Scoring Formula section |
| SCOR-02 | Rank results by score descending | Sort ScreenedStock list by score field descending after all survivors scored |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `alpaca-py` | 0.43.2 | Asset universe + bar fetching + optionable check | Already installed; `get_all_assets()` with `GetAssetsRequest` for universe; `StockHistoricalDataClient` for bars |
| `finnhub-python` | 2.4.27 | Fundamental data (profile + metrics) | Already installed; `FinnhubClient` wrapper built in Phase 2 |
| `ta` | 0.11.0 | RSI(14) and SMA(200) computation | Already installed; used by `compute_indicators()` built in Phase 2 |
| `pandas` | >=1.5 | DataFrame operations for bars, HV computation | Already installed; required by alpaca-py and ta |
| `numpy` | 2.4.2 | Log returns and standard deviation for HV | Already installed; required by pandas |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `math` | stdlib | `math.log`, `math.sqrt` for HV computation (or use numpy equivalents) | Historical volatility calculation |
| `pathlib` | stdlib | Read symbol_list.txt | Merging existing symbols into universe |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| HV from daily bars | Alpaca OptionsSnapshot.implied_volatility | IV is more accurate for premium prediction, but requires 1 API call per symbol (~200+ calls); HV is free from already-fetched bars |
| HV from daily bars | Finnhub beta metric | Beta measures market correlation not absolute volatility; HV is more directly useful for premium yield estimation |
| Single pipeline.py | Split into filters.py + scoring.py + pipeline.py | More files but better separation; recommend single pipeline.py for this scope since filters are small functions |

**Installation:**
```bash
# No new dependencies needed -- all libraries already installed
```

## Architecture Patterns

### Recommended Project Structure
```
screener/
  __init__.py              # (existing)
  config_loader.py         # (existing) ScreenerConfig, load_config
  finnhub_client.py        # (existing) FinnhubClient, extract_metric
  market_data.py           # (existing) fetch_daily_bars, compute_indicators
  pipeline.py              # (NEW) run_pipeline(), Stage 1/2/3 functions
models/
  screened_stock.py         # (existing) ScreenedStock, FilterResult
```

### Pattern 1: Universe Fetch with Optionable Pre-computation
**What:** Make 2 upfront Alpaca API calls to build the full universe and optionable set, avoiding per-symbol option checks later.
**When to use:** At pipeline start, before any filtering.
**Example:**
```python
# Source: Alpaca API docs + verified alpaca-py 0.43.2 SDK inspection
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass, AssetStatus

def fetch_universe(trade_client) -> tuple[list[str], set[str]]:
    """Return (all_symbols, optionable_symbols) from Alpaca.

    Makes 2 API calls total:
    1. All active tradable US equities
    2. All assets with options_enabled attribute
    """
    # Call 1: All active, tradable US equities
    all_req = GetAssetsRequest(
        asset_class=AssetClass.US_EQUITY,
        status=AssetStatus.ACTIVE,
    )
    all_assets = trade_client.get_all_assets(all_req)
    tradable = [a for a in all_assets if a.tradable]
    all_symbols = [a.symbol for a in tradable]

    # Call 2: Options-enabled assets only
    opt_req = GetAssetsRequest(attributes="options_enabled")
    opt_assets = trade_client.get_all_assets(opt_req)
    optionable_set = {a.symbol for a in opt_assets}

    return all_symbols, optionable_set
```

### Pattern 2: Historical Volatility from Daily Bars
**What:** Compute annualized HV as standard deviation of log returns, using bars already fetched for technical indicators.
**When to use:** In Stage 1, after compute_indicators, before scoring. Reuses the same bars DataFrame.
**Example:**
```python
# Source: Standard quantitative finance formula
import numpy as np

def compute_historical_volatility(bars_df, window: int = 30) -> float | None:
    """Compute annualized HV from daily close prices.

    Args:
        bars_df: DataFrame with 'close' column (from Alpaca bars).
        window: Number of trading days for rolling window.

    Returns:
        Annualized volatility as float, or None if insufficient data.
    """
    close = bars_df["close"]
    if len(close) < window + 1:
        return None
    # Use last `window` days of log returns
    log_returns = np.log(close / close.shift(1)).dropna()
    recent_returns = log_returns.iloc[-window:]
    if len(recent_returns) < window:
        return None
    daily_std = recent_returns.std()
    annualized_hv = float(daily_std * np.sqrt(252))
    return annualized_hv
```

### Pattern 3: Filter Function with FilterResult Recording
**What:** Each filter is a small function that takes a ScreenedStock + config, returns FilterResult, and appends it to the stock's filter_results list.
**When to use:** Every filter in Stage 1 and Stage 2.
**Example:**
```python
from models.screened_stock import FilterResult

def filter_price_range(stock, config) -> FilterResult:
    """FILT-05: Check price is within configured range."""
    if stock.price is None:
        return FilterResult(
            filter_name="price_range",
            passed=False,
            reason="Price data unavailable",
        )
    in_range = config.technicals.price_min <= stock.price <= config.technicals.price_max
    return FilterResult(
        filter_name="price_range",
        passed=in_range,
        actual_value=stock.price,
        threshold=config.technicals.price_max,
        reason="" if in_range else f"Price {stock.price} outside [{config.technicals.price_min}, {config.technicals.price_max}]",
    )
```

### Pattern 4: Stage Short-Circuit
**What:** Run all filters within a stage (to populate FilterResults for all), but skip subsequent stages if any filter in current stage failed.
**When to use:** Between Stage 1 and Stage 2, between Stage 2 and Stage 3.
**Example:**
```python
def run_stage_1(stock, config, optionable_set):
    """Run all cheap Alpaca-based filters. Returns True if all passed."""
    results = [
        filter_price_range(stock, config),
        filter_avg_volume(stock, config),
        filter_rsi(stock, config),
        filter_sma200(stock, config),
    ]
    for r in results:
        stock.filter_results.append(r)
    return all(r.passed for r in results)
```

### Anti-Patterns to Avoid
- **Per-symbol optionable API call:** Do NOT call `get_option_contracts()` per symbol to check if options exist. Use the bulk `get_all_assets(attributes="options_enabled")` call instead. Saves ~200 API calls.
- **Fetching IV during screening:** Do NOT call `get_option_chain()` per symbol during the screening pipeline. Each call returns the full option chain and counts against the 200 req/min limit. HV from bars is free.
- **Fetching bars for eliminated stocks:** Do NOT fetch bars for all 8,000+ symbols. Fetch bars only for symbols that need Stage 1 filtering -- but since price/volume/RSI/SMA all come from bars, all symbols need bars. Optimize by batching at 20 symbols per request (already implemented in market_data.py).
- **Scoring stocks that failed filters:** Only score stocks that passed ALL filters (Stage 1 + Stage 2). Do not waste computation scoring failures.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RSI computation | Custom RSI calculator | `ta.momentum.RSIIndicator` | Already implemented in compute_indicators(); edge cases handled |
| SMA computation | Custom moving average | `ta.trend.SMAIndicator` | Already implemented; handles NaN, insufficient data |
| Rate limiting | Custom token bucket | `FinnhubClient._throttle()` | Already built in Phase 2 with 429 retry |
| Metric extraction | Manual dict key lookups | `extract_metric()` with fallback chains | Already built in Phase 2; handles None, missing keys |
| Config validation | Manual threshold checks | `ScreenerConfig` Pydantic models | Already built in Phase 1; type-safe, validated |
| Filter result tracking | Ad-hoc pass/fail dicts | `FilterResult` dataclass + `ScreenedStock.filter_results` | Already built in Phase 2; passed_all_filters property |

**Key insight:** Phases 1 and 2 built all the data-fetching and configuration infrastructure. Phase 3 is primarily glue code: call existing functions, apply filter logic, compute scores. The filter functions themselves are simple comparisons.

## Common Pitfalls

### Pitfall 1: Finnhub marketCapitalization Units
**What goes wrong:** Comparing raw Finnhub marketCapitalization against config.fundamentals.market_cap_min without unit conversion.
**Why it happens:** Finnhub's `company_profile2` returns `marketCapitalization` in MILLIONS (e.g., AAPL = ~2,800,000 meaning $2.8 trillion). The config `market_cap_min` is set to 2,000,000,000 (2 billion in raw dollars).
**How to avoid:** Multiply Finnhub's `marketCapitalization` by 1,000,000 before comparing, OR store the config threshold in millions. Choose one convention and document it clearly.
**Warning signs:** Every stock passes or every stock fails the market cap filter.

### Pitfall 2: Alpaca Bar Fetch for 8,000+ Symbols
**What goes wrong:** Attempting to fetch bars for all ~8,000 tradable equities overwhelms memory and takes 400+ API calls (at batch_size=20).
**Why it happens:** The decision says all symbols start in the universe and bars are needed for Stage 1 filters.
**How to avoid:** This is expected behavior -- ~400 batched calls at 200 req/min = ~2 minutes. No throttle needed for Alpaca (200 req/min is generous). Log progress. Consider: the `fetch_daily_bars` function already batches at 20. With 8,000 symbols: 400 batches. Each returns multi-symbol data. This is the intended "cheap" stage.
**Warning signs:** Pipeline hangs or OOM. Monitor memory with large DataFrames. Consider processing in chunks if memory is an issue.

### Pitfall 3: Missing Bar Data = Silent Elimination
**What goes wrong:** Symbols with no Alpaca bar data get silently dropped from results without a FilterResult.
**Why it happens:** `fetch_daily_bars` silently skips symbols not in the response. If a stock has no bar data, it won't have price/volume/RSI/SMA populated, so filters would fail -- but the pipeline must still create a ScreenedStock and record FilterResults.
**How to avoid:** After bar fetching, iterate ALL universe symbols. For symbols with no bars, create ScreenedStock with a "no_bar_data" FilterResult. This ensures Phase 4 can report elimination counts accurately.
**Warning signs:** Total (passing + eliminated) count is less than universe size.

### Pitfall 4: Finnhub Profile Empty Response for Delisted/Obscure Stocks
**What goes wrong:** `company_profile()` returns `{}` for some symbols (not found in Finnhub). Without handling, `marketCapitalization` extraction fails with KeyError.
**Why it happens:** Finnhub doesn't cover all Alpaca-tradable stocks. Some micro-caps, recent IPOs, or OTC-listed stocks have no Finnhub data.
**How to avoid:** Check if profile is empty dict before extracting fields. Empty profile = fail all Finnhub-dependent filters with appropriate FilterResult reason.
**Warning signs:** FinnhubAPIException or KeyError during Stage 2 for specific symbols.

### Pitfall 5: Scoring Division by Zero
**What goes wrong:** Capital efficiency component uses `1 / price` or similar formula. Price = 0 or None causes crash.
**Why it happens:** Edge case where price filtering should have eliminated zero-price stocks, but a bug skips the check.
**How to avoid:** Only score stocks that passed ALL filters (which includes price range filter). Add defensive check in scoring function.
**Warning signs:** ZeroDivisionError in scoring.

### Pitfall 6: HV = None for Low-History Stocks
**What goes wrong:** Stocks with fewer than 31 bars cannot compute 30-day historical volatility. Using None in scoring formula crashes.
**Why it happens:** Recent IPOs, recently re-listed stocks may have insufficient trading history.
**How to avoid:** If HV is None, assign a neutral/median volatility score (0.5 normalized) rather than failing the stock entirely. HV is for scoring, not filtering -- a stock shouldn't be eliminated just because it's new.
**Warning signs:** Stocks passing all filters but getting None score.

## Code Examples

### Scoring Formula (SCOR-01)

Recommended 3-component weighted scoring:

```python
# Scoring weights (capital efficiency > volatility > fundamentals)
WEIGHT_CAPITAL_EFFICIENCY = 0.45
WEIGHT_VOLATILITY = 0.35
WEIGHT_FUNDAMENTALS = 0.20

def compute_wheel_score(stock, all_passing_stocks) -> float:
    """Compute wheel suitability score (0-100 scale).

    Components:
    1. Capital efficiency: Lower price = more contracts per dollar = higher score
    2. Volatility proxy: Higher HV = higher premiums = higher score
    3. Fundamental strength: Composite of margin + growth + low debt

    All components normalized to 0-1, then weighted and scaled to 0-100.
    """
    # --- Capital Efficiency (0-1) ---
    # Lower price stocks are more capital-efficient for wheel strategy
    # Normalize: price_min gets 1.0, price_max gets 0.0 (linear interpolation)
    prices = [s.price for s in all_passing_stocks if s.price]
    min_p, max_p = min(prices), max(prices)
    if max_p == min_p:
        cap_eff = 0.5
    else:
        cap_eff = 1.0 - (stock.price - min_p) / (max_p - min_p)

    # --- Volatility Proxy (0-1) ---
    # Higher HV = higher option premiums = better for wheel
    hvs = [s.hv_30 for s in all_passing_stocks if s.hv_30 is not None]
    if hvs and stock.hv_30 is not None:
        min_hv, max_hv = min(hvs), max(hvs)
        if max_hv == min_hv:
            vol_score = 0.5
        else:
            vol_score = (stock.hv_30 - min_hv) / (max_hv - min_hv)
    else:
        vol_score = 0.5  # neutral if HV unavailable

    # --- Fundamental Strength (0-1) ---
    # Composite: higher margin + higher growth + lower debt = stronger
    fund_components = []
    if stock.net_margin is not None:
        # Normalize margin: 0% = 0.0, 30%+ = 1.0
        fund_components.append(min(stock.net_margin / 30.0, 1.0))
    if stock.sales_growth is not None:
        # Normalize growth: 0% = 0.0, 30%+ = 1.0
        fund_components.append(min(max(stock.sales_growth, 0) / 30.0, 1.0))
    if stock.debt_equity is not None:
        # Lower debt is better: 0 = 1.0, 1.0+ = 0.0
        fund_components.append(max(1.0 - stock.debt_equity, 0.0))

    fund_score = sum(fund_components) / len(fund_components) if fund_components else 0.5

    # --- Weighted composite ---
    raw = (
        WEIGHT_CAPITAL_EFFICIENCY * cap_eff
        + WEIGHT_VOLATILITY * vol_score
        + WEIGHT_FUNDAMENTALS * fund_score
    )
    return round(raw * 100, 2)
```

### Pipeline Orchestration

```python
def run_pipeline(
    trade_client,
    stock_client,
    finnhub_client,
    config: ScreenerConfig,
    symbol_list_path: str = "config/symbol_list.txt",
) -> list[ScreenedStock]:
    """Run the full 3-stage screening pipeline.

    Returns ALL ScreenedStock objects (passing and eliminated).
    Callers use stock.passed_all_filters to separate winners.
    """
    # 1. Fetch universe + optionable set (2 API calls)
    all_symbols, optionable_set = fetch_universe(trade_client)

    # 1b. Merge existing symbol_list.txt
    existing = load_symbol_list(symbol_list_path)
    universe = sorted(set(all_symbols) | set(existing))

    # 2. Fetch bars for entire universe (batched, ~400 calls)
    bars = fetch_daily_bars(stock_client, universe, num_bars=250, batch_size=20)

    # 3. Create ScreenedStock objects, populate indicators + HV
    stocks = []
    for sym in universe:
        stock = ScreenedStock.from_symbol(sym)
        if sym in bars:
            indicators = compute_indicators(bars[sym])
            stock.price = indicators["price"]
            stock.avg_volume = indicators["avg_volume"]
            stock.rsi_14 = indicators["rsi_14"]
            stock.sma_200 = indicators["sma_200"]
            stock.above_sma200 = indicators["above_sma200"]
            stock.hv_30 = compute_historical_volatility(bars[sym])
        stocks.append(stock)

    # 4. Stage 1: Cheap Alpaca filters
    for stock in stocks:
        if stock.price is None:
            stock.filter_results.append(FilterResult("bar_data", False, reason="No bar data"))
            continue
        stage1_passed = run_stage_1_filters(stock, config)
        if not stage1_passed:
            continue  # skip Stage 2

        # 5. Stage 2: Expensive Finnhub filters + optionable
        run_stage_2_filters(stock, config, finnhub_client, optionable_set)

    # 6. Stage 3: Score survivors
    passing = [s for s in stocks if s.passed_all_filters]
    for stock in passing:
        stock.score = compute_wheel_score(stock, passing)

    # 7. Sort by score descending
    stocks.sort(key=lambda s: (s.score or 0), reverse=True)

    return stocks
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-symbol option contract lookup for optionable check | `GetAssetsRequest(attributes="options_enabled")` bulk query | Available in alpaca-py 0.43.x | Saves ~200 API calls; single call returns all optionable symbols |
| Finnhub metric keys as single known strings | Fallback key chains with multiple suffixes | Established Phase 2 | Handles Finnhub's inconsistent metric naming |

**Deprecated/outdated:**
- `alpaca-trade-api-python` (old SDK): Replaced by `alpaca-py`. This project already uses `alpaca-py`.

## Open Questions

1. **Exact count of optionable symbols from Alpaca**
   - What we know: `GetAssetsRequest(attributes="options_enabled")` returns options-eligible assets. ~4,000-5,000 US equities typically have listed options.
   - What's unclear: Exact count may vary. The returned set should be intersected with active/tradable assets.
   - Recommendation: Log the count at INFO level during pipeline run. If the set is surprisingly small (<1,000), investigate.

2. **Alpaca bar fetch performance for 8,000+ symbols**
   - What we know: 400+ batches of 20 = 400+ API calls. Alpaca rate limit is 200 req/min. This means ~2-3 minutes of bar fetching.
   - What's unclear: Memory footprint of 8,000 DataFrames each with 250 rows. Rough estimate: ~200MB, manageable.
   - Recommendation: Log batch progress. If memory is an issue, process in chunks of 1000 symbols at a time (fetch bars -> compute indicators -> discard bars).

3. **ScreenedStock needs hv_30 field**
   - What we know: The existing `ScreenedStock` dataclass does not have an `hv_30` field. It needs one for historical volatility.
   - What's unclear: Whether to add it to ScreenedStock or compute it inline during scoring.
   - Recommendation: Add `hv_30: Optional[float] = None` field to `ScreenedStock` for consistency with the progressive-population pattern. This also enables Phase 4 to display HV in output tables.

4. **Finnhub marketCapitalization units**
   - What we know: Finnhub returns `marketCapitalization` in MILLIONS (e.g., 2800000 for $2.8T). Config `market_cap_min` defaults to 2,000,000,000 (2 billion dollars).
   - What's unclear: Whether to adjust config or adjust comparison.
   - Recommendation: Multiply Finnhub's value by 1,000,000 before comparing against config. This keeps config in raw dollars (human-readable) and documents the conversion clearly.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | None (defaults work; tests run from /tmp per Phase 1 pattern) |
| Quick run command | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/ -x -q` |
| Full suite command | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FILT-01 | Market cap filter excludes below minimum | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestMarketCapFilter -x` | No -- Wave 0 |
| FILT-02 | Debt/equity filter excludes above maximum | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestDebtEquityFilter -x` | No -- Wave 0 |
| FILT-03 | Net margin filter excludes below minimum | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestNetMarginFilter -x` | No -- Wave 0 |
| FILT-04 | Sales growth filter excludes below minimum | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestSalesGrowthFilter -x` | No -- Wave 0 |
| FILT-05 | Price range filter excludes outside min/max | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestPriceRangeFilter -x` | No -- Wave 0 |
| FILT-06 | Volume filter excludes below minimum | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestVolumeFilter -x` | No -- Wave 0 |
| FILT-07 | RSI filter excludes overbought (above max) | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestRSIFilter -x` | No -- Wave 0 |
| FILT-08 | SMA200 filter excludes below SMA | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestSMA200Filter -x` | No -- Wave 0 |
| FILT-09 | Optionable filter excludes non-optionable | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestOptionableFilter -x` | No -- Wave 0 |
| FILT-10 | Sector filter excludes disallowed sectors | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestSectorFilter -x` | No -- Wave 0 |
| SCOR-01 | Score computed with 3 weighted components | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestScoring -x` | No -- Wave 0 |
| SCOR-02 | Results sorted by score descending | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestScoreSorting -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd /tmp && python -m pytest tests/test_pipeline.py -x -q`
- **Per wave merge:** `cd /tmp && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_pipeline.py` -- all filter unit tests (FILT-01 through FILT-10), scoring tests (SCOR-01, SCOR-02), pipeline integration test
- [ ] Add `hv_30` field to `models/screened_stock.py` -- needed before filter/scoring tests can reference it
- [ ] No new framework install needed -- pytest 9.0.2 already configured and working

## Sources

### Primary (HIGH confidence)
- `alpaca-py` 0.43.2 SDK -- inspected installed model classes directly via Python REPL:
  - `Asset.model_fields`: confirmed `attributes: Optional[List[str]]` field
  - `GetAssetsRequest.model_fields`: confirmed `status`, `asset_class`, `exchange`, `attributes` parameters
  - `OptionsSnapshot.model_fields`: confirmed `implied_volatility: Optional[float]` and `greeks: Optional[OptionsGreeks]`
  - `OptionChainRequest.model_fields`: confirmed `underlying_symbol`, filter params
  - `TradingClient` methods: confirmed `get_all_assets`, `get_option_contracts`, `get_asset`
- Existing codebase: `screener/config_loader.py`, `screener/finnhub_client.py`, `screener/market_data.py`, `models/screened_stock.py`, `core/broker_client.py`

### Secondary (MEDIUM confidence)
- [Alpaca Options Trading docs](https://docs.alpaca.markets/docs/options-trading) -- confirmed `options_enabled` attribute filter
- [Alpaca Working with Assets docs](https://docs.alpaca.markets/docs/working-with-assets) -- confirmed `get_all_assets` usage
- [Alpaca SDK Models docs](https://alpaca.markets/sdks/python/api_reference/data/models.html) -- confirmed OptionsSnapshot fields
- [Alpaca SDK Trading Requests docs](https://alpaca.markets/sdks/python/api_reference/trading/requests.html) -- confirmed GetAssetsRequest parameters
- [Alpaca How To Trade Options guide](https://alpaca.markets/learn/how-to-trade-options-with-alpaca) -- confirmed `GetAssetsRequest(attributes="options_enabled")` pattern
- [Alpaca Support - Rate Limits](https://alpaca.markets/support/usage-limit-api-calls) -- confirmed 200 req/min limit

### Tertiary (LOW confidence)
- Finnhub `beta` metric availability -- confirmed via WebSearch that basic_financials includes `beta` key, but exact key name not verified against live API call. Not critical since HV is the primary volatility proxy.
- Exact count of tradable US equities on Alpaca (~8,000+) -- commonly cited figure but not verified against current API response.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and verified via REPL inspection
- Architecture: HIGH -- builds directly on Phase 1-2 infrastructure with well-defined patterns
- Pitfalls: HIGH -- identified from code inspection and API documentation, verified unit conversions
- Scoring formula: MEDIUM -- weights are discretionary; formula pattern is sound but exact weights need tuning
- Optionable check via attributes: HIGH -- verified via SDK model inspection and official docs

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable -- all libraries pinned, Alpaca API stable)