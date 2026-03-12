# Phase 2: Data Sources - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Fetch fundamental data from Finnhub API and compute technical indicators (RSI-14, SMA-200) from Alpaca daily bars. Handle Finnhub rate limits (60 calls/min free tier) and missing/null data gracefully. No filtering logic, no scoring, no CLI entry points -- those are later phases.

</domain>

<decisions>
## Implementation Decisions

### Rate Limiting Strategy
- Simple sleep throttle (~1 second between Finnhub calls) to stay under 60 calls/min
- Per-symbol sequential pattern: fetch profile + metrics for one symbol before moving to next
- On 429 response: retry once after 5s backoff, if still 429 skip that symbol and continue (don't crash the whole run)
- Debug-level logging for each API call (symbol, endpoint, response time) -- silent by default, visible with --log-level DEBUG

### Missing Data Handling
- Missing/null metric values = fail the filter (can't verify the criterion, conservative approach for wheel strategy)
- Fallback key chains for Finnhub metric keys (try primary key first, fall back to alternates, e.g., 'marketCapitalization' then 'mktCapitalization')
- Completely empty Finnhub response (symbol not found): log WARNING and skip symbol
- Track skip/failure counts by reason (e.g., "N symbols skipped due to missing Finnhub data", "M symbols skipped due to insufficient bar history") for Phase 4 filter summary

### Technical Indicators
- Use `ta` library for RSI(14) and SMA(200) computation (ta.momentum.RSIIndicator, ta.trend.SMAIndicator)
- Fetch 250 daily bars (~1 trading year) from Alpaca per symbol -- covers SMA(200) with buffer for holidays/weekends
- Multi-symbol batch request for Alpaca bars (StockBarsRequest supports multiple symbols)
- Insufficient bar history (<200 bars) = fail the SMA200 filter; RSI(14) may still compute with 30+ bars

### Finnhub Client Design
- Lightweight FinnhubClient class (follows BrokerClient pattern) with rate limiter state and API key
- Uses official `finnhub-python` SDK (`finnhub.Client(api_key=key)`)
- Lives in `screener/finnhub_client.py` (screener-specific, not core infrastructure)

### Alpaca Market Data Module
- Separate `screener/market_data.py` for Alpaca bar fetching + ta indicator computation
- Does NOT extend BrokerClient -- keeps screener logic separate from trading code
- Uses existing Alpaca credentials from config/credentials.py

### Claude's Discretion
- Exact sleep duration between Finnhub calls (1s baseline, adjust based on research)
- Specific Finnhub metric key fallback chains (determined during research against live API docs)
- Internal data flow between FinnhubClient, market_data module, and ScreenedStock population
- How to handle the `logging/` package shadow for new modules (pattern established in Phase 1)

</decisions>

<specifics>
## Specific Ideas

- ScreenedStock progressive build: fetch Alpaca bars first (cheap, no rate limit), compute indicators, then fetch Finnhub data (rate limited) -- this ordering enables cheap-first filtering in Phase 3
- STATE.md flags from Phase 1: "Finnhub metric key mapping (TTM vs Quarterly vs Annual suffixes) needs live API validation early in Phase 2" and "Alpaca multi-symbol bar request behavior needs verification"
- The 60 calls/min rate limit with 2 calls/symbol means ~30 symbols/min for Finnhub data -- 200 symbols takes ~7 minutes

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config/credentials.py`: `require_finnhub_key()` returns API key or raises with instructions -- use directly in FinnhubClient
- `core/broker_client.py`: `StockHistoricalDataClientSigned` wraps Alpaca stock data client -- market_data.py can use same credential pattern
- `models/screened_stock.py`: `ScreenedStock` dataclass with Optional fields for price, avg_volume, market_cap, debt_equity, net_margin, sales_growth, rsi_14, sma_200, sector, raw_finnhub_profile, raw_finnhub_metrics, raw_alpaca_bars

### Established Patterns
- BrokerClient class wraps SDK clients with UserAgentMixin -- FinnhubClient follows similar wrapper pattern
- Alpaca snapshot batching in BrokerClient.get_option_snapshot (100 per batch) -- market_data.py can follow this for bar requests
- `import logging as stdlib_logging` pattern to avoid project's logging/ shadow

### Integration Points
- `screener/` package already exists (config_loader.py, __init__.py) -- new modules go here
- `config/credentials.py` provides API keys for both Finnhub and Alpaca
- `models/screened_stock.py` ScreenedStock fields map to data fetched in this phase

</code_context>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 02-data-sources*
*Context gathered: 2026-03-07*
