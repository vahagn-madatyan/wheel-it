# Requirements: Wheeely v1.1 -- Screener Fix + Covered Calls

**Defined:** 2026-03-11
**Core Value:** Automatically identify wheel-strategy-suitable stocks by combining fundamental health checks with technical screening, replacing manual symbol selection with data-driven filtering.

## v1.1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Pipeline Fix

- [ ] **FIX-01**: Screener produces non-zero results when run with moderate preset against live market data
- [ ] **FIX-02**: Finnhub debt/equity values are normalized correctly (percentage-to-ratio conversion if needed, verified with diagnostic script)
- [ ] **FIX-03**: Missing Finnhub data (None values) for any single metric does not eliminate a stock -- stock passes filter with neutral score instead
- [ ] **FIX-04**: avg_volume_min is differentiated across presets (conservative=1M, moderate=500K, aggressive=200K)

### Preset Overhaul

- [ ] **PRES-01**: All three presets differ across ALL filter categories (fundamentals, technicals, options, earnings)
- [ ] **PRES-02**: Conservative preset uses tighter thresholds (large-cap, low delta, high OI, strict spread)
- [ ] **PRES-03**: Aggressive preset uses looser thresholds (small-cap OK, wider delta range, lower OI minimum)
- [ ] **PRES-04**: Each preset includes default sector avoid/prefer lists (conservative favors stable sectors, aggressive excludes nothing)

### HV Percentile Filter

- [ ] **HVPR-01**: User can filter stocks by HV Percentile rank (30-day HV percentile over 252-day lookback)
- [ ] **HVPR-02**: HV Percentile threshold is configurable per preset (conservative>=50, moderate>=30, aggressive>=20)
- [ ] **HVPR-03**: HV Percentile value is displayed in screener results table

### Earnings Calendar

- [ ] **EARN-01**: User can filter stocks that have earnings within N days (default 14)
- [ ] **EARN-02**: Earnings data is fetched via Finnhub earnings calendar endpoint (free tier)
- [ ] **EARN-03**: Earnings day threshold is configurable per preset (conservative>=21, moderate>=14, aggressive>=7)

### Options Chain Validation

- [ ] **OPTS-01**: User can filter stocks by options chain OI (minimum open interest on nearest ATM put)
- [ ] **OPTS-02**: User can filter stocks by bid/ask spread (maximum spread on nearest ATM put)
- [ ] **OPTS-03**: OI and spread thresholds are configurable per preset
- [ ] **OPTS-04**: Options chain validation runs only on stocks that pass all prior filter stages
- [ ] **OPTS-05**: Best put premium (annualized yield) is displayed in screener results table for each passing stock

### Covered Call Screening

- [ ] **CALL-01**: User can run `run-call-screener` standalone CLI to screen covered call opportunities
- [ ] **CALL-02**: Call screener accepts symbol + cost basis (from Alpaca positions or user input) and finds best call to sell
- [ ] **CALL-03**: Call screener enforces strike >= cost basis (never sell below cost basis)
- [ ] **CALL-04**: Call screener applies same DTE/OI/spread/delta filters as put screening (configurable via presets)
- [ ] **CALL-05**: Call screener displays Rich table with symbol, cost basis, recommended strike, DTE, premium, delta, annualized return
- [ ] **CALL-06**: `run-strategy` integrates call screener to select covered calls for assigned positions

## Future Requirements

Deferred to v1.2+. Tracked but not in current roadmap.

### Display Enhancements

- **DISP-01**: HV vs IV comparison column in results table
- **DISP-02**: Cost basis tracking from strategy logs (accumulated premiums)

### Position Management

- **PMGT-01**: Rolling recommendation when position hits 50% profit
- **PMGT-02**: Position P&L display from current option prices vs premium received

## Out of Scope

| Feature | Reason |
|---------|--------|
| Paid IV data (ORATS, Barchart) | User decided free APIs only -- HV Percentile is adequate proxy |
| Backtesting screener results | Separate domain, doubles scope, historical option data expensive |
| Real-time streaming screener | Wheel trades happen weekly, batch CLI sufficient |
| Custom filter expression language | Over-engineering for personal tool -- YAML overrides sufficient |
| ML-based stock selection | Black box, rule-based filters match documented strategy |
| Multi-symbol covered call optimization | Portfolio-level Greeks too complex -- screen each position independently |
| Finviz scraping | Unreliable, ToS violation -- Finnhub API already integrated |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIX-01 | Phase 7 | Pending |
| FIX-02 | Phase 7 | Pending |
| FIX-03 | Phase 7 | Pending |
| FIX-04 | Phase 7 | Pending |
| PRES-01 | Phase 7 | Pending |
| PRES-02 | Phase 7 | Pending |
| PRES-03 | Phase 7 | Pending |
| PRES-04 | Phase 7 | Pending |
| HVPR-01 | Phase 8 | Pending |
| HVPR-02 | Phase 8 | Pending |
| HVPR-03 | Phase 8 | Pending |
| EARN-01 | Phase 8 | Pending |
| EARN-02 | Phase 8 | Pending |
| EARN-03 | Phase 8 | Pending |
| OPTS-01 | Phase 9 | Pending |
| OPTS-02 | Phase 9 | Pending |
| OPTS-03 | Phase 9 | Pending |
| OPTS-04 | Phase 9 | Pending |
| OPTS-05 | Phase 9 | Pending |
| CALL-01 | Phase 10 | Pending |
| CALL-02 | Phase 10 | Pending |
| CALL-03 | Phase 10 | Pending |
| CALL-04 | Phase 10 | Pending |
| CALL-05 | Phase 10 | Pending |
| CALL-06 | Phase 10 | Pending |

**Coverage:**
- v1.1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0

---
*Requirements defined: 2026-03-11*
*Last updated: 2026-03-11 after roadmap creation*
