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
