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
