# Phase 2: Data Sources - Research

**Researched:** 2026-03-08
**Domain:** Finnhub fundamental data fetching, Alpaca bar retrieval, technical indicator computation, rate limiting
**Confidence:** HIGH

## Summary

This phase builds two data-fetching modules: a `FinnhubClient` for fundamental data (company profile + basic financials metrics) and a `market_data` module for Alpaca daily bar retrieval plus RSI(14)/SMA(200) computation via the `ta` library. The critical complexity lies in Finnhub rate limiting (60 calls/min free tier), the undocumented nature of Finnhub metric key names (requiring fallback chains), and the Alpaca multi-symbol `limit` gotcha where the limit parameter caps total bars across ALL symbols, not per-symbol.

The `finnhub-python` SDK (v2.4.27) provides a thin wrapper over the REST API. The `ta` library (v0.11.0, already installed) provides `RSIIndicator` and `SMAIndicator` classes that accept pandas Series and return computed indicators. Alpaca's `StockBarsRequest` supports multi-symbol requests but requires careful handling of the limit parameter and split-adjusted data.

**Primary recommendation:** Fetch Alpaca bars in batches of ~20 symbols (to keep per-symbol bar count manageable without pagination) with no `limit` parameter, then fetch Finnhub data sequentially with 1-second sleep between calls. Use `Adjustment.SPLIT` for bar data to get correct historical prices for indicator computation.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Simple sleep throttle (~1 second between Finnhub calls) to stay under 60 calls/min
- Per-symbol sequential pattern: fetch profile + metrics for one symbol before moving to next
- On 429 response: retry once after 5s backoff, if still 429 skip that symbol and continue (don't crash the whole run)
- Debug-level logging for each API call (symbol, endpoint, response time)
- Missing/null metric values = fail the filter (conservative approach)
- Fallback key chains for Finnhub metric keys (try primary key first, fall back to alternates)
- Completely empty Finnhub response (symbol not found): log WARNING and skip symbol
- Track skip/failure counts by reason for Phase 4 filter summary
- Use `ta` library for RSI(14) and SMA(200) computation
- Fetch 250 daily bars (~1 trading year) from Alpaca per symbol
- Multi-symbol batch request for Alpaca bars
- Insufficient bar history (<200 bars) = fail SMA200 filter; RSI(14) may still compute with 30+ bars
- Lightweight FinnhubClient class in `screener/finnhub_client.py`
- Separate `screener/market_data.py` for Alpaca bar fetching + ta indicator computation
- Does NOT extend BrokerClient -- keeps screener logic separate from trading code
- Uses existing Alpaca credentials from config/credentials.py
- Uses official `finnhub-python` SDK

### Claude's Discretion
- Exact sleep duration between Finnhub calls (1s baseline, adjust based on research)
- Specific Finnhub metric key fallback chains (determined during research against live API docs)
- Internal data flow between FinnhubClient, market_data module, and ScreenedStock population
- How to handle the `logging/` package shadow for new modules (pattern established in Phase 1)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SAFE-02 | Finnhub API calls are rate-limited to respect 60 calls/min free tier limit | FinnhubClient with time.sleep throttle + 429 retry logic; rate limit verified at 60/min (see Rate Limiting section) |
| SAFE-04 | Screener handles missing/null Finnhub metric values gracefully with fallback key chains | Metric key fallback chains documented; None-safe extraction pattern with `.get()` chains (see Finnhub Metric Keys section) |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `finnhub-python` | 2.4.27 | Official Finnhub API client | Official SDK, wraps REST API, returns plain dicts |
| `ta` | 0.11.0 | RSI(14) and SMA(200) computation | Pure Python, no C compilation, Pandas-native, already installed |
| `alpaca-py` | 0.43.2 | Alpaca daily bar retrieval via StockBarsRequest | Already in project, provides StockHistoricalDataClient |
| `pandas` | >=1.5 | DataFrame for bar data, Series for ta library input | Already in project, required by both alpaca-py and ta |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `time` | stdlib | Sleep-based rate limiting | Between each Finnhub API call |
| `datetime` | stdlib | Bar date range computation | Setting start date for 250 trading days |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ta` (bukosabino) | `TA-Lib` (C library) | TA-Lib is faster but requires C compilation; ta is pure Python, already installed, sufficient for 200 symbols |
| `ta` (bukosabino) | `pandas-ta` | pandas-ta has more indicators but ta is simpler, already installed, and covers RSI + SMA |
| Manual rate limiter | `ratelimit` PyPI package | Sleep-based throttle is simpler and sufficient for sequential per-symbol pattern |

**Installation:**
```bash
uv pip install finnhub-python
```

Note: `ta` (0.11.0) is already installed. `finnhub-python` must be added to `pyproject.toml` dependencies.

## Architecture Patterns

### Recommended Project Structure
```
screener/
    __init__.py          # existing
    config_loader.py     # existing (Phase 1)
    finnhub_client.py    # NEW: FinnhubClient class
    market_data.py       # NEW: Alpaca bars + ta indicators
models/
    screened_stock.py    # existing (Phase 1) -- populated by this phase
config/
    credentials.py       # existing -- provides require_finnhub_key() and Alpaca keys
```

### Pattern 1: FinnhubClient with Built-in Rate Limiting
**What:** A lightweight client class wrapping the `finnhub-python` SDK with automatic sleep-based rate limiting and retry logic.
**When to use:** Every Finnhub API call goes through this client.
**Example:**
```python
# Source: verified against finnhub-python SDK and Finnhub API docs
import logging as stdlib_logging
import time
import finnhub
from config.credentials import require_finnhub_key

logger = stdlib_logging.getLogger(__name__)

class FinnhubClient:
    def __init__(self, api_key: str | None = None, call_interval: float = 1.1):
        self._key = api_key or require_finnhub_key()
        self._client = finnhub.Client(api_key=self._key)
        self._call_interval = call_interval  # seconds between calls
        self._last_call_time: float = 0.0

    def _throttle(self):
        """Sleep to respect rate limit."""
        elapsed = time.monotonic() - self._last_call_time
        if elapsed < self._call_interval:
            time.sleep(self._call_interval - elapsed)
        self._last_call_time = time.monotonic()

    def _call_with_retry(self, func, *args, symbol: str = "", endpoint: str = ""):
        """Call Finnhub API with throttle, retry on 429."""
        self._throttle()
        start = time.monotonic()
        try:
            result = func(*args)
            duration = time.monotonic() - start
            logger.debug("%s %s completed in %.2fs", symbol, endpoint, duration)
            return result
        except finnhub.FinnhubAPIException as e:
            if e.status_code == 429:
                logger.warning("%s %s got 429, retrying after 5s", symbol, endpoint)
                time.sleep(5)
                self._throttle()
                return func(*args)  # second attempt, let exception propagate
            raise

    def company_profile(self, symbol: str) -> dict:
        return self._call_with_retry(
            self._client.company_profile2, symbol=symbol, endpoint="profile2"
        )

    def company_metrics(self, symbol: str) -> dict:
        return self._call_with_retry(
            self._client.company_basic_financials, symbol, "all",
            symbol=symbol, endpoint="basic_financials"
        )
```

### Pattern 2: Multi-Symbol Alpaca Bar Fetching (Batched)
**What:** Fetch daily bars for multiple symbols using `StockBarsRequest`, batched to avoid the limit-total-across-symbols gotcha.
**When to use:** Getting historical price data for indicator computation.
**Example:**
```python
# Source: verified against alpaca-py 0.43.2 SDK and Alpaca forum findings
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment
from datetime import datetime, timedelta
import pandas as pd

def fetch_daily_bars(
    client: StockHistoricalDataClient,
    symbols: list[str],
    num_bars: int = 250,
    batch_size: int = 20,
) -> dict[str, pd.DataFrame]:
    """Fetch daily bars for symbols in batches, return dict of DataFrames."""
    # ~365 calendar days covers ~250 trading days
    end = datetime.now()
    start = end - timedelta(days=int(num_bars * 1.5))

    all_bars: dict[str, pd.DataFrame] = {}

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i : i + batch_size]
        request = StockBarsRequest(
            symbol_or_symbols=batch,
            timeframe=TimeFrame.Day,
            start=start,
            adjustment=Adjustment.SPLIT,  # critical for correct indicator values
            # DO NOT set limit -- let it return all bars to avoid per-symbol truncation
        )
        barset = client.get_stock_bars(request)
        df = barset.df
        # df has a multi-index: (symbol, timestamp)
        for sym in batch:
            try:
                sym_df = df.loc[sym].copy()
                all_bars[sym] = sym_df
            except KeyError:
                pass  # symbol not found in response

    return all_bars
```

### Pattern 3: Indicator Computation
**What:** Compute RSI(14) and SMA(200) from bar DataFrames using the `ta` library.
**When to use:** After fetching bars, before populating ScreenedStock.
**Example:**
```python
# Source: verified against ta 0.11.0 installed locally
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator
import pandas as pd

def compute_indicators(bars_df: pd.DataFrame) -> dict:
    """Compute RSI(14) and SMA(200) from a single symbol's bar DataFrame.

    Args:
        bars_df: DataFrame with 'close' column (from Alpaca bars).

    Returns:
        dict with 'rsi_14', 'sma_200', 'price', 'above_sma200' keys.
    """
    close = bars_df["close"]
    result = {"price": float(close.iloc[-1])}

    # RSI(14) -- needs at least ~30 bars for meaningful values
    if len(close) >= 30:
        rsi = RSIIndicator(close=close, window=14)
        rsi_series = rsi.rsi()
        result["rsi_14"] = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else None
    else:
        result["rsi_14"] = None

    # SMA(200) -- needs at least 200 bars
    if len(close) >= 200:
        sma = SMAIndicator(close=close, window=200)
        sma_series = sma.sma_indicator()
        sma_val = float(sma_series.iloc[-1]) if not pd.isna(sma_series.iloc[-1]) else None
        result["sma_200"] = sma_val
        if sma_val is not None:
            result["above_sma200"] = result["price"] > sma_val
        else:
            result["above_sma200"] = None
    else:
        result["sma_200"] = None
        result["above_sma200"] = None

    return result
```

### Pattern 4: Logging Module Shadow Handling
**What:** Use `import logging as stdlib_logging` to avoid the project's `logging/` package shadow.
**When to use:** In every new module in `screener/`.
**Example:**
```python
# Source: established pattern from Phase 1 (screener/config_loader.py line 3)
import logging as stdlib_logging
logger = stdlib_logging.getLogger(__name__)
```

### Anti-Patterns to Avoid
- **Setting `limit` on multi-symbol StockBarsRequest:** The limit is TOTAL across all symbols, not per-symbol. With 20 symbols and limit=250, you'd get ~12 bars per symbol. Omit limit entirely and let Alpaca return all available bars.
- **Using `Adjustment.RAW` for bar data:** Raw prices don't account for stock splits, producing incorrect SMA/RSI values for stocks that have split. Always use `Adjustment.SPLIT` (or `Adjustment.ALL` if dividend adjustment matters).
- **Calling Finnhub without throttle:** Even with only 200 symbols (400 calls), bursting requests will quickly trigger 429 errors. The 60/min limit means ~1 call per second is the safe maximum.
- **Catching broad exceptions on Finnhub calls:** Catch `finnhub.FinnhubAPIException` specifically. A generic `except Exception` could mask connection errors or auth failures.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RSI computation | Manual RSI formula | `ta.momentum.RSIIndicator` | RSI has initialization period nuances (Wilder's smoothing); ta handles it correctly |
| SMA computation | Manual rolling mean | `ta.trend.SMAIndicator` | Simple, but using ta keeps indicator computation in one library; consistent NaN handling |
| Finnhub HTTP calls | Raw `requests.get()` | `finnhub.Client()` from `finnhub-python` | Handles auth, URL construction, response parsing; thin wrapper but saves boilerplate |
| Bar data fetching | Raw Alpaca REST calls | `StockHistoricalDataClient.get_stock_bars()` | Handles pagination, auth, response parsing; returns BarSet with `.df` property |

**Key insight:** The `finnhub-python` SDK is extremely thin (just wraps REST calls into methods returning dicts), but it handles auth token injection and URL construction. The `ta` library's value is in correct RSI initialization (Wilder's smoothing method) which is easy to get wrong when hand-rolling.

## Common Pitfalls

### Pitfall 1: Finnhub Metric Key Naming Uncertainty
**What goes wrong:** Finnhub's API docs do not enumerate the exact metric key names in the `metric` object. Keys use camelCase with suffixes like `TTM`, `Annual`, `Quarterly`, `5Y`.
**Why it happens:** Finnhub documents 117 metrics but only describes the response shape (`metric: {}` map), not individual keys.
**How to avoid:** Implement fallback key chains and validate against a real API call early (Wave 0 or first task). Known keys from research:
  - Market cap: `marketCapitalization` (in company_profile2 response, NOT in basic_financials)
  - Debt/Equity: try `totalDebtToEquity` first, fallback `totalDebtToEquityQuarterly`, `totalDebtToEquityAnnual`
  - Net margin: try `netProfitMarginTTM` first, fallback `netProfitMarginAnnual`, `netMargin`
  - Sales growth: try `revenueGrowthQuarterlyYoy` first, fallback `revenueGrowth5Y`, `revenueGrowth3Y`
**Warning signs:** Getting `None` for every symbol on a particular metric = wrong key name.

### Pitfall 2: Alpaca Multi-Symbol `limit` Parameter
**What goes wrong:** Setting `limit=250` with multiple symbols returns only 250 bars TOTAL, split unevenly across symbols. Some symbols get full data, others get truncated or zero bars.
**Why it happens:** The `limit` parameter in Alpaca's bars API caps the total response size, not per-symbol.
**How to avoid:** Do NOT set `limit` on multi-symbol requests. Instead, set a generous `start` date (375+ calendar days back for 250 trading days) and let Alpaca return all bars. Batch symbols in groups of ~20 to keep response sizes manageable.
**Warning signs:** Getting fewer bars than expected for symbols at the end of the list.

### Pitfall 3: Finnhub Rate Limit Arithmetic
**What goes wrong:** 200 symbols x 2 API calls each (profile + metrics) = 400 calls. At 60/min, this takes ~7 minutes. Developers expect faster execution.
**Why it happens:** Each symbol requires two separate Finnhub calls (company_profile2 for market cap/sector, company_basic_financials for ratios).
**How to avoid:** Document the expected ~7 minute runtime for 200 symbols. Consider fetching Alpaca bars first (no rate limit, fast multi-symbol) before the slow Finnhub sequential calls. This matches the CONTEXT.md "cheap-first" ordering suggestion.
**Warning signs:** 429 errors after the first 60 symbols.

### Pitfall 4: NaN Values in ta Library Output
**What goes wrong:** RSIIndicator and SMAIndicator produce NaN values for the first N rows (14 for RSI, 200 for SMA). Taking `iloc[-1]` on a short series returns NaN, which is not the same as `None`.
**Why it happens:** Moving averages and RSI require a warm-up period. `pd.isna(float('nan'))` is True but `float('nan') is None` is False.
**How to avoid:** Always check `pd.isna()` on the last value before converting to float. Convert NaN to None for ScreenedStock fields.
**Warning signs:** ScreenedStock fields containing `float('nan')` instead of `None`, causing downstream comparison errors.

### Pitfall 5: Finnhub company_basic_financials Returns Empty for Some Symbols
**What goes wrong:** Small-cap or recently-IPO'd stocks may return `{'metric': {}, 'series': {}}` with an empty metric dict.
**Why it happens:** Finnhub doesn't have fundamental data for all symbols.
**How to avoid:** Check `if not response.get('metric')` before accessing keys. Log a WARNING and mark the symbol as skipped due to missing Finnhub data.
**Warning signs:** KeyError or TypeError when accessing `response['metric']['keyName']` on empty responses.

### Pitfall 6: Finnhub FinnhubAPIException Import
**What goes wrong:** The exception class for 429 handling needs to be imported correctly.
**Why it happens:** The finnhub-python SDK exposes `finnhub.FinnhubAPIException` with a `status_code` attribute.
**How to avoid:** Verify the exception class import path and attribute name during implementation. The SDK raises `FinnhubAPIException` with `.status_code` for HTTP errors.
**Warning signs:** Unhandled exceptions on 429 responses.

## Code Examples

### Finnhub Metric Key Extraction with Fallback Chains
```python
# Source: research-derived pattern; keys need live API validation (see Open Questions)

# Fallback chains: try keys in order, return first non-None value
METRIC_FALLBACK_CHAINS = {
    "debt_equity": [
        "totalDebtToEquity",
        "totalDebtToEquityQuarterly",
        "totalDebtToEquityAnnual",
    ],
    "net_margin": [
        "netProfitMarginTTM",
        "netProfitMarginAnnual",
        "netMargin",
    ],
    "sales_growth": [
        "revenueGrowthQuarterlyYoy",
        "revenueGrowth5Y",
        "revenueGrowth3Y",
    ],
}

def extract_metric(metrics: dict, chain_name: str) -> float | None:
    """Extract a metric value using fallback key chain.

    Args:
        metrics: The 'metric' dict from Finnhub basic_financials response.
        chain_name: Key into METRIC_FALLBACK_CHAINS.

    Returns:
        First non-None value from the chain, or None if all keys missing/null.
    """
    chain = METRIC_FALLBACK_CHAINS.get(chain_name, [])
    for key in chain:
        value = metrics.get(key)
        if value is not None:
            return float(value)
    return None
```

### Populating ScreenedStock from API Data
```python
# Source: models/screened_stock.py field names + research patterns

def populate_stock(
    stock: ScreenedStock,
    profile: dict,
    metrics: dict,
    indicators: dict,
) -> ScreenedStock:
    """Populate a ScreenedStock with fetched data.

    Args:
        stock: Existing ScreenedStock (has symbol set).
        profile: Finnhub company_profile2 response.
        metrics: Finnhub basic_financials['metric'] dict.
        indicators: Dict from compute_indicators().
    """
    # From profile2
    stock.market_cap = profile.get("marketCapitalization")
    stock.sector = profile.get("finnhubIndustry")

    # From basic_financials metrics (with fallback chains)
    stock.debt_equity = extract_metric(metrics, "debt_equity")
    stock.net_margin = extract_metric(metrics, "net_margin")
    stock.sales_growth = extract_metric(metrics, "sales_growth")

    # From Alpaca bars + ta computation
    stock.price = indicators.get("price")
    stock.rsi_14 = indicators.get("rsi_14")
    stock.sma_200 = indicators.get("sma_200")
    stock.above_sma200 = indicators.get("above_sma200")

    return stock
```

### Finnhub SDK Call Patterns
```python
# Source: verified against finnhub-python 2.4.27 SDK

import finnhub

client = finnhub.Client(api_key="your_key")

# Company profile2 -- returns dict with marketCapitalization, finnhubIndustry, etc.
profile = client.company_profile2(symbol="AAPL")
# Returns: {'country': 'US', 'currency': 'USD', 'exchange': 'NASDAQ NMS - GLOBAL MARKET',
#           'finnhubIndustry': 'Technology', 'ipo': '1980-12-12',
#           'logo': '...', 'marketCapitalization': 2800000, 'name': 'Apple Inc',
#           'phone': '...', 'shareOutstanding': 15000, 'ticker': 'AAPL', 'weburl': '...'}

# Company basic financials -- returns dict with 'metric', 'metricType', 'series', 'symbol'
financials = client.company_basic_financials("AAPL", "all")
# financials['metric'] is a dict with ~117 keys
# financials['series'] has 'annual' and 'quarterly' time-series data
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `finnhub-python` 2.4.x | `finnhub-python` 2.4.27 | Jan 2026 | No breaking changes; thin SDK wrapper remains stable |
| `ta` 0.10.x | `ta` 0.11.0 | Nov 2023 | Last release; stable, no known issues with Python 3.13 |
| Alpaca v1 API | alpaca-py 0.43.2 | Current | StockBarsRequest with multi-symbol support; `.df` returns multi-index DataFrame |

**Deprecated/outdated:**
- Alpaca v1 Python SDK (`alpaca-trade-api`): replaced by `alpaca-py`; do not use
- `ta-lib` Python wrapper: requires C library compilation; `ta` (pure Python) is preferred for this project's scale

## Open Questions

1. **Exact Finnhub Metric Key Names**
   - What we know: The basic_financials endpoint returns ~117 metric keys in camelCase. Keys like `totalDebtToEquity`, `netProfitMarginTTM` are referenced in community code but the official docs don't enumerate them.
   - What's unclear: The exact spelling/suffix for debt/equity, net margin, and sales growth keys. TTM vs Annual vs Quarterly suffixes vary by metric.
   - Recommendation: First implementation task should include a "discovery call" -- fetch basic_financials for AAPL, print all metric keys, and finalize the fallback chains. This is flagged in STATE.md as a research item.

2. **Alpaca Multi-Symbol Pagination Behavior**
   - What we know: With no `limit` set and a `start` date, Alpaca returns all available bars. The SDK handles pagination internally.
   - What's unclear: Whether very large multi-symbol requests (200+ symbols) cause timeouts or memory issues.
   - Recommendation: Batch in groups of 20 symbols (confirmed working in community usage). Monitor response times and adjust batch size if needed.

3. **Finnhub `company_profile2` vs `company_basic_financials` for Market Cap**
   - What we know: `marketCapitalization` is confirmed in `company_profile2` response. It may also exist in `basic_financials.metric` under a different key.
   - What's unclear: Whether we can get market cap from basic_financials to reduce from 2 API calls to 1 per symbol.
   - Recommendation: Keep 2-call pattern (profile + metrics) as designed. Market cap in profile2 is reliable and also provides sector/industry data. Attempting to optimize to 1 call risks missing sector data.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already configured, 30 tests passing) |
| Config file | `tests/conftest.py` (exists with fixtures) |
| Quick run command | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/ -x -q` |
| Full suite command | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/ -v` |

Note: Tests run from `/tmp` to avoid the project's `logging/` package shadowing Python's stdlib `logging` during pytest import (established pattern from Phase 1).

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SAFE-02 | Finnhub API calls rate-limited to 60/min | unit (mock time.sleep, verify throttle logic) | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/test_finnhub_client.py -x` | Wave 0 |
| SAFE-02 | 429 retry with 5s backoff, skip on second failure | unit (mock FinnhubAPIException) | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/test_finnhub_client.py -x` | Wave 0 |
| SAFE-04 | Missing metric values handled via fallback chains | unit (synthetic metric dicts) | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/test_finnhub_client.py -x` | Wave 0 |
| SAFE-04 | Empty Finnhub response skipped with warning | unit (empty response dict) | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/test_finnhub_client.py -x` | Wave 0 |
| N/A | RSI(14) computed correctly from close prices | unit (known input/output) | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/test_market_data.py -x` | Wave 0 |
| N/A | SMA(200) computed correctly from close prices | unit (known input/output) | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/test_market_data.py -x` | Wave 0 |
| N/A | Insufficient bars (<200) results in sma_200=None | unit (short series) | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/test_market_data.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/ -x -q`
- **Per wave merge:** `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_finnhub_client.py` -- covers SAFE-02 (rate limiting, 429 retry) and SAFE-04 (fallback chains, empty responses)
- [ ] `tests/test_market_data.py` -- covers RSI/SMA computation, insufficient bar handling, multi-symbol batching
- [ ] Framework install: `uv pip install finnhub-python` -- finnhub-python not yet installed
- [ ] pyproject.toml update: add `finnhub-python` and `ta` to dependencies

## Sources

### Primary (HIGH confidence)
- `ta` library v0.11.0 -- locally installed, API verified via `inspect.signature()`: `RSIIndicator(close, window=14, fillna=False).rsi()` and `SMAIndicator(close, window, fillna=False).sma_indicator()`
- `alpaca-py` v0.43.2 -- locally installed, API verified: `StockBarsRequest` fields, `Adjustment` enum values (RAW, SPLIT, DIVIDEND, ALL)
- Finnhub company_profile2 response keys -- verified from [Finnhub API docs](https://finnhub.io/docs/api/company-profile2): `marketCapitalization`, `finnhubIndustry`, `ticker`, etc.
- Finnhub company_basic_financials response structure -- verified from [Finnhub API docs](https://finnhub.io/docs/api/company-basic-financials): returns `{metric: {}, metricType: str, series: {}, symbol: str}`

### Secondary (MEDIUM confidence)
- Finnhub rate limit: 60 calls/min free tier -- from [Finnhub pricing](https://finnhub.io/pricing) and [rate limit docs](https://finnhub.io/docs/api/rate-limit), plus 30 calls/second hard limit across all tiers
- Alpaca multi-symbol `limit` gotcha -- verified from [Alpaca community forum](https://forum.alpaca.markets/t/get-stock-bars-for-multiple-assets/16618): limit is total bars across all symbols, not per-symbol
- `finnhub-python` v2.4.27 -- from [PyPI](https://pypi.org/project/finnhub-python/), released Jan 2026
- `finnhub.FinnhubAPIException` with `.status_code` -- from SDK source structure

### Tertiary (LOW confidence)
- Exact Finnhub metric key names (`totalDebtToEquity`, `netProfitMarginTTM`, `revenueGrowthQuarterlyYoy`) -- inferred from community code patterns and WebSearch results. **Needs live API validation in Wave 0/first task.** The official docs do not enumerate individual metric keys.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries locally installed and API signatures verified
- Architecture: HIGH -- patterns follow established Phase 1 conventions (logging shadow, module placement, credential usage)
- Pitfalls: HIGH -- multi-symbol limit gotcha verified from official forum; rate limit confirmed from docs
- Finnhub metric keys: LOW -- exact key names not confirmed from official docs; community patterns suggest the listed names but live validation required

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (30 days -- stable libraries, APIs unlikely to change)
