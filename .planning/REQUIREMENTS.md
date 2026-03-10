# Requirements: Wheeely Stock Screener

**Defined:** 2026-03-07
**Core Value:** Automatically identify wheel-strategy-suitable stocks by combining fundamental health checks with technical screening

## v1 Requirements

### Screening Filters

- [x] **FILT-01**: Screener filters stocks by market cap minimum (e.g., mid-cap and above) using Finnhub data
- [x] **FILT-02**: Screener filters stocks by debt/equity ratio maximum using Finnhub data
- [x] **FILT-03**: Screener filters stocks by net margin minimum (positive) using Finnhub data
- [x] **FILT-04**: Screener filters stocks by quarterly sales growth minimum using Finnhub data
- [x] **FILT-05**: Screener filters stocks by price range (min/max) using Alpaca market data
- [x] **FILT-06**: Screener filters stocks by minimum average daily volume using Alpaca market data
- [x] **FILT-07**: Screener filters stocks by RSI(14) maximum (not overbought) using Alpaca bars + ta library
- [x] **FILT-08**: Screener filters stocks where price is above SMA(200) using Alpaca bars + ta library
- [x] **FILT-09**: Screener filters stocks that are optionable (have listed options) using Alpaca options data
- [x] **FILT-10**: Screener filters stocks by GICS sector/industry using Finnhub profile data

### Scoring

- [x] **SCOR-01**: Screener scores each passing stock for wheel strategy suitability based on premium yield potential, capital efficiency, and fundamental strength
- [x] **SCOR-02**: Screener ranks results by score descending

### Configuration

- [x] **CONF-01**: User can define screening filter thresholds in a YAML config file (config/screener.yaml)
- [x] **CONF-02**: Screener ships with preset profiles: conservative, moderate, and aggressive (config/presets/)
- [x] **CONF-03**: User can override individual preset values with custom values in screener.yaml
- [x] **CONF-04**: Config is validated via Pydantic models with clear error messages for invalid values

### Output

- [x] **OUTP-01**: Screener displays results as a rich formatted table showing symbol, price, volume, key metrics, and score
- [x] **OUTP-02**: Screener shows filter summary with per-stage elimination counts (universe -> price -> volume -> fundamentals -> technicals -> final)
- [x] **OUTP-03**: Screener can export filtered symbols to config/symbol_list.txt via --update-symbols flag
- [x] **OUTP-04**: Screener shows progress indicator during rate-limited API calls

### CLI Integration

- [ ] **CLI-01**: User can run screener standalone via `run-screener` CLI command
- [ ] **CLI-02**: User can run screener before strategy via `run-strategy --screen` flag
- [x] **CLI-03**: Screener CLI accepts --update-symbols flag to write results to symbol_list.txt
- [ ] **CLI-04**: Screener CLI accepts --output-only flag (default) to display results without updating files

### Data & Safety

- [x] **SAFE-01**: Finnhub API key is loaded from .env file (FINNHUB_API_KEY)
- [x] **SAFE-02**: Finnhub API calls are rate-limited to respect 60 calls/min free tier limit
- [x] **SAFE-03**: Symbol list export protects actively-traded symbols (short puts, assigned shares, short calls) from removal
- [x] **SAFE-04**: Screener handles missing/null Finnhub metric values gracefully with fallback key chains

## v2 Requirements

### Enhanced Output

- **OUTP-05**: Screener shows options chain preview alongside each result (best put strike, premium, delta)
- **OUTP-06**: Screener supports --dry-run mode showing what would change in symbol_list.txt

### Performance

- **PERF-01**: Screener caches Finnhub responses with configurable TTL to avoid repeated API calls
- **PERF-02**: Screener supports --verbose flag showing per-symbol filter decisions

### Advanced Filters

- **FILT-11**: User can define custom filter expressions beyond predefined fields

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time streaming screener | Batch screening sufficient for wheel strategy (trades weekly, not intraday) |
| Web dashboard | CLI-only tool; web UI adds major complexity |
| Backtesting engine | Separate domain; doubles project scope |
| AI/ML screening | Over-engineering; rule-based filters are transparent and debuggable |
| Multi-broker support | Only Alpaca is used; abstraction adds no value |
| Alert/notification system | Screener runs on-demand, not continuously |
| Finviz scraping | Using Finnhub API instead for reliable fundamental data |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FILT-01 | Phase 3 | Complete |
| FILT-02 | Phase 3 | Complete |
| FILT-03 | Phase 3 | Complete |
| FILT-04 | Phase 3 | Complete |
| FILT-05 | Phase 3 | Complete |
| FILT-06 | Phase 3 | Complete |
| FILT-07 | Phase 3 | Complete |
| FILT-08 | Phase 3 | Complete |
| FILT-09 | Phase 3 | Complete |
| FILT-10 | Phase 3 | Complete |
| SCOR-01 | Phase 3 | Complete |
| SCOR-02 | Phase 3 | Complete |
| CONF-01 | Phase 1 | Complete |
| CONF-02 | Phase 1 | Complete |
| CONF-03 | Phase 1 | Complete |
| CONF-04 | Phase 1 | Complete |
| OUTP-01 | Phase 4 | Complete |
| OUTP-02 | Phase 4 | Complete |
| OUTP-03 | Phase 5 | Complete |
| OUTP-04 | Phase 4 | Complete |
| CLI-01 | Phase 5 | Pending |
| CLI-02 | Phase 5 | Pending |
| CLI-03 | Phase 5 | Complete |
| CLI-04 | Phase 5 | Pending |
| SAFE-01 | Phase 1 | Complete |
| SAFE-02 | Phase 2 | Complete |
| SAFE-03 | Phase 5 | Complete |
| SAFE-04 | Phase 2 | Complete |

**Coverage:**
- v1 requirements: 28 total
- Mapped to phases: 28
- Unmapped: 0

---
*Requirements defined: 2026-03-07*
*Last updated: 2026-03-07 after roadmap creation*
