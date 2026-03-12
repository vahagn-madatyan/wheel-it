# Phase 3: Screening Pipeline - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Filter a universe of stocks through 10 screening filters (fundamental, technical, options-availability), score survivors for wheel-strategy suitability, and return ranked results. No CLI entry points, no display formatting, no symbol export — those are later phases.

</domain>

<decisions>
## Implementation Decisions

### Stock Universe Source
- Use ALL Alpaca-tradable US equities as the starting universe (~8,000+ symbols)
- Query Alpaca's asset API for active, tradable stocks — single fast call
- Merge existing `config/symbol_list.txt` symbols into the universe so currently-traded symbols are always re-evaluated
- No curated seed list — maximize discovery of new wheel candidates

### Pipeline Stages & Filter Ordering
- 3-stage pipeline: **Alpaca → Finnhub → Score**
  - Stage 1 (Alpaca/cheap): Price range, average volume, RSI(14), SMA(200), above_sma200 — all from already-fetched bar data
  - Stage 2 (Finnhub/expensive): Market cap, debt/equity, net margin, sales growth, sector, optionable — requires API calls
  - Stage 3: Score all survivors, sort descending
- Short-circuit between stages: run all filters within a stage (record each FilterResult), but skip subsequent stages if any filter in current stage failed
- This means Finnhub calls only happen for stocks that pass ALL cheap Alpaca filters

### Scoring Formula
- **Capital efficiency first** — prioritize stocks where tied-up capital generates the most premium
- Three scoring components: premium yield potential (via volatility proxy), capital efficiency, fundamental strength
- Capital efficiency weighted highest
- **IV/Volatility data source:** Research needed — investigate Alpaca options snapshots for actual IV, Finnhub volatility data, and other IV rank APIs. Fall back to historical volatility from daily bars (annualized std dev of returns) if no better source found
- **Normalized 0-100 scale** — each component normalized to 0-1, weighted, scaled to 0-100 for interpretability
- Return all passing stocks scored and sorted (no top-N limit)

### Sector Filtering
- Case-insensitive exact match against Finnhub's `finnhubIndustry` values
- Empty `include` list = all sectors allowed (only `exclude` list removes sectors)
- Missing/null sector data from Finnhub = fail the sector filter (consistent with Phase 2 missing data = fail policy)

### Pipeline Return Data
- Return ALL ScreenedStock objects (both passing and eliminated) with their FilterResults populated
- Phase 4 needs eliminated stocks for per-filter elimination count reporting
- Callers use `passed_all_filters` property to separate winners from losers

### Claude's Discretion
- Exact scoring formula weights (capital efficiency > volatility > fundamentals, but exact ratios TBD)
- Historical volatility computation details (if used as fallback)
- Internal module structure (single pipeline.py vs split by stage)
- How to check optionable status via Alpaca API
- Batch size for Alpaca bar fetching across 8,000+ symbols

</decisions>

<specifics>
## Specific Ideas

- The existing `core/strategy.py` has a scoring formula for OPTIONS: `(1 - |delta|) * (250 / (DTE + 5)) * (bid / strike)`. The STOCK screening score is different — it evaluates the underlying, not the option contract
- Phase 2 context note: "ScreenedStock progressive build: fetch Alpaca bars first (cheap, no rate limit), compute indicators, then fetch Finnhub data (rate limited) — this ordering enables cheap-first filtering in Phase 3"
- With cheap-first filtering, expect ~8,000 → ~200-500 after Alpaca filters → ~50-150 after Finnhub filters → all scored and returned

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `screener/config_loader.py`: `ScreenerConfig` with `FundamentalsConfig`, `TechnicalsConfig`, `OptionsConfig`, `SectorsConfig` — all filter thresholds ready to use
- `models/screened_stock.py`: `ScreenedStock` dataclass with progressive Optional fields + `FilterResult` tracking + `passed_all_filters` property
- `screener/finnhub_client.py`: `FinnhubClient` with rate limiting, 429 retry, `extract_metric()` with fallback chains
- `screener/market_data.py`: `fetch_daily_bars()` (batched) and `compute_indicators()` (RSI, SMA, price, volume)
- `core/strategy.py`: Pattern reference for filter → score → select pipeline (used for options, similar flow for stocks)

### Established Patterns
- `import logging as stdlib_logging` to avoid logging/ shadow
- Progressive data population on dataclasses (from_symbol → add fields)
- Batch API requests (BrokerClient batches snapshots at 100, market_data batches bars at 20)

### Integration Points
- `screener/` package — pipeline module(s) go here
- `ScreenerConfig` provides all filter thresholds
- `ScreenedStock.from_symbol()` creates the initial object, pipeline populates fields
- `fetch_daily_bars()` expects `StockHistoricalDataClient` (not `BrokerClient`) — pass `broker_client.stock_client`

</code_context>

<deferred>
## Deferred Ideas

- Finnhub response caching with TTL (v2 requirement PERF-01)
- Per-symbol verbose filter decisions (v2 requirement PERF-02)

</deferred>

---

*Phase: 03-screening-pipeline*
*Context gathered: 2026-03-08*
