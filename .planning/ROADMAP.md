# Roadmap: Wheeely Stock Screener

## Milestones

- ✅ **v1.0 Stock Screener** -- Phases 1-6 (shipped 2026-03-11)
- 🚧 **v1.1 Screener Fix + Covered Calls** -- Phases 7-10 (in progress)

## Phases

<details>
<summary>✅ v1.0 Stock Screener (Phases 1-6) -- SHIPPED 2026-03-11</summary>

- [x] Phase 1: Foundation (2/2 plans) -- completed 2026-03-08
- [x] Phase 2: Data Sources (2/2 plans) -- completed 2026-03-08
- [x] Phase 3: Screening Pipeline (2/2 plans) -- completed 2026-03-09
- [x] Phase 4: Output and Display (2/2 plans) -- completed 2026-03-09
- [x] Phase 5: CLI and Integration (3/3 plans) -- completed 2026-03-10
- [x] Phase 6: Packaging & Tech Debt Cleanup (1/1 plan) -- completed 2026-03-11

</details>

### v1.1 Screener Fix + Covered Calls

- [ ] **Phase 7: Pipeline Fix + Preset Overhaul** - Fix zero-result bug and differentiate preset profiles across all filter categories
- [ ] **Phase 8: HV Rank + Earnings Calendar** - Add volatility ranking and earnings proximity filtering as cheap pre-filters
- [ ] **Phase 9: Options Chain Validation** - Validate surviving stocks have tradeable options with sufficient OI and tight spreads
- [ ] **Phase 10: Covered Call Screening** - Screen and recommend covered calls for assigned wheel positions

## Phase Details

### Phase 7: Pipeline Fix + Preset Overhaul
**Goal**: Users get actionable screening results from all three presets, with each preset enforcing meaningfully different filter strictness
**Depends on**: Phase 6 (v1.0 complete)
**Requirements**: FIX-01, FIX-02, FIX-03, FIX-04, PRES-01, PRES-02, PRES-03, PRES-04
**Success Criteria** (what must be TRUE):
  1. Running `run-screener --preset moderate` against live market data produces at least one surviving stock
  2. Stocks with missing Finnhub metrics (None values) appear in results instead of being silently eliminated
  3. Running the screener with conservative, moderate, and aggressive presets produces noticeably different survivor counts and score distributions
  4. Each preset includes sector avoid/prefer lists visible in the YAML config files
  5. Finnhub debt/equity values match expected ranges when compared against a known reference (e.g., AAPL D/E ~1.5-2.0x)
**Plans**: TBD

Plans:
- [ ] 07-01: TBD
- [ ] 07-02: TBD

### Phase 8: HV Rank + Earnings Calendar
**Goal**: Users can assess premium richness via volatility ranking and avoid selling options into upcoming earnings events
**Depends on**: Phase 7
**Requirements**: HVPR-01, HVPR-02, HVPR-03, EARN-01, EARN-02, EARN-03
**Success Criteria** (what must be TRUE):
  1. Screener results table displays an HV Percentile column with values between 0-100 for each surviving stock
  2. Stocks with earnings within the configured threshold (default 14 days) are excluded from results
  3. HV Percentile and earnings-day thresholds differ across conservative, moderate, and aggressive presets
  4. Both filters run before any per-symbol options chain API calls (cheap-first ordering preserved)
**Plans**: TBD

Plans:
- [ ] 08-01: TBD
- [ ] 08-02: TBD

### Phase 9: Options Chain Validation
**Goal**: Users see only stocks that have actually tradeable options with real liquidity, not just "optionable" tickers with dead chains
**Depends on**: Phase 8
**Requirements**: OPTS-01, OPTS-02, OPTS-03, OPTS-04, OPTS-05
**Success Criteria** (what must be TRUE):
  1. Stocks surviving all prior filters are further filtered by minimum open interest on the nearest ATM put
  2. Stocks with bid/ask spreads exceeding the configured maximum on the nearest ATM put are eliminated
  3. OI and spread thresholds are configurable per preset and differ across conservative/moderate/aggressive
  4. Screener results table displays the best put premium as annualized yield for each passing stock
  5. Options chain validation runs only after all fundamental, technical, HV rank, and earnings filters have passed
**Plans**: TBD

Plans:
- [ ] 09-01: TBD
- [ ] 09-02: TBD

### Phase 10: Covered Call Screening
**Goal**: Users with assigned stock positions can find the best covered call to sell, completing the wheel's second leg
**Depends on**: Phase 9
**Requirements**: CALL-01, CALL-02, CALL-03, CALL-04, CALL-05, CALL-06
**Success Criteria** (what must be TRUE):
  1. User can run `run-call-screener` as a standalone CLI and see recommended covered calls for their positions
  2. Call screener accepts a symbol and cost basis, and never recommends a strike below cost basis
  3. Call screener applies DTE, OI, spread, and delta filters consistent with preset configuration
  4. Results display as a Rich table showing symbol, cost basis, recommended strike, DTE, premium, delta, and annualized return
  5. Running `run-strategy` on assigned positions automatically selects covered calls using the call screener logic
**Plans**: TBD

Plans:
- [ ] 10-01: TBD
- [ ] 10-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 7 -> 8 -> 9 -> 10

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 2/2 | Complete | 2026-03-08 |
| 2. Data Sources | v1.0 | 2/2 | Complete | 2026-03-08 |
| 3. Screening Pipeline | v1.0 | 2/2 | Complete | 2026-03-09 |
| 4. Output and Display | v1.0 | 2/2 | Complete | 2026-03-09 |
| 5. CLI and Integration | v1.0 | 3/3 | Complete | 2026-03-10 |
| 6. Packaging & Tech Debt | v1.0 | 1/1 | Complete | 2026-03-11 |
| 7. Pipeline Fix + Preset Overhaul | v1.1 | 0/0 | Not started | - |
| 8. HV Rank + Earnings Calendar | v1.1 | 0/0 | Not started | - |
| 9. Options Chain Validation | v1.1 | 0/0 | Not started | - |
| 10. Covered Call Screening | v1.1 | 0/0 | Not started | - |
