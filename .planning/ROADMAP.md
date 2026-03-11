# Roadmap: Wheeely Stock Screener

## Overview

This roadmap delivers a stock screening module for the Wheeely options wheel strategy bot. The screener combines Finnhub fundamental data with Alpaca technical/options data to automatically identify wheel-strategy-suitable stocks, replacing manual symbol selection. The work progresses from configuration and data models, through API client integration, into the core filtering and scoring pipeline, then output rendering, and finally CLI integration with position-safe symbol export.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - YAML config with presets, Pydantic validation, data models, and Finnhub API key setup
- [ ] **Phase 2: Data Sources** - Finnhub API client with rate limiting and Alpaca bar-based technical indicators
- [ ] **Phase 3: Screening Pipeline** - All 10 filters, scoring engine, and pipeline orchestration with cheap-first ordering
- [ ] **Phase 4: Output and Display** - Rich table rendering, filter elimination summary, and progress indicator
- [ ] **Phase 5: CLI and Integration** - Standalone screener command, strategy integration flag, and position-safe symbol export
- [ ] **Phase 6: Packaging & Tech Debt Cleanup** - Missing pyproject.toml dependencies, CLI error formatting, test isolation fixes

## Phase Details

### Phase 1: Foundation
**Goal**: Users can configure screening criteria through YAML config files with preset profiles, and the system validates all configuration with clear error messages
**Depends on**: Nothing (first phase)
**Requirements**: CONF-01, CONF-02, CONF-03, CONF-04, SAFE-01
**Success Criteria** (what must be TRUE):
  1. User can create a screener.yaml file with filter thresholds and the system loads it without error
  2. User can select a preset profile (conservative, moderate, aggressive) and see different filter thresholds applied
  3. User can override individual preset values in screener.yaml and the overrides take effect
  4. User receives clear, actionable error messages when screener.yaml contains invalid values (wrong types, out-of-range, missing required fields)
  5. Adding FINNHUB_API_KEY to .env makes it available to the screener without code changes
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md -- Config loader with presets, Pydantic validation, and ScreenedStock data model
- [x] 01-02-PLAN.md -- Finnhub API key loading in credentials.py

### Phase 2: Data Sources
**Goal**: The screener can fetch fundamental data from Finnhub and compute technical indicators from Alpaca bars, handling rate limits and missing data gracefully
**Depends on**: Phase 1
**Requirements**: SAFE-02, SAFE-04
**Success Criteria** (what must be TRUE):
  1. Screening 200+ symbols completes without hitting Finnhub 429 rate limit errors
  2. Symbols with missing or null Finnhub metric values (market cap, debt/equity, margins, growth) are handled gracefully via fallback key chains rather than crashing
  3. RSI(14) and SMA(200) values are computed correctly from Alpaca daily bars for any given symbol
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md -- FinnhubClient with rate limiting, 429 retry, and metric fallback chains
- [ ] 02-02-PLAN.md -- Alpaca bar fetching and RSI(14)/SMA(200) indicator computation

### Phase 3: Screening Pipeline
**Goal**: The screener filters a universe of stocks through fundamental, technical, and options-availability checks, then scores and ranks survivors for wheel suitability
**Depends on**: Phase 2
**Requirements**: FILT-01, FILT-02, FILT-03, FILT-04, FILT-05, FILT-06, FILT-07, FILT-08, FILT-09, FILT-10, SCOR-01, SCOR-02
**Success Criteria** (what must be TRUE):
  1. Stocks below the configured market cap minimum are excluded from results
  2. Stocks failing any configured filter (debt/equity, net margin, sales growth, price range, volume, RSI, SMA200, optionable, sector) are excluded from results
  3. The pipeline applies cheap Alpaca filters before expensive Finnhub filters to minimize API calls
  4. Each surviving stock has a wheel-suitability score based on premium yield potential, capital efficiency, and fundamental strength
  5. Results are returned sorted by score descending
**Plans**: 2 plans

Plans:
- [ ] 03-01-PLAN.md -- All 10 filter functions, HV computation, stage runners, and hv_30 field on ScreenedStock
- [ ] 03-02-PLAN.md -- Scoring engine (3 weighted components) and pipeline orchestrator (universe fetch, 3-stage flow, sort)

### Phase 4: Output and Display
**Goal**: Users can see screening results in a clear, informative format with visibility into what was filtered and why
**Depends on**: Phase 3
**Requirements**: OUTP-01, OUTP-02, OUTP-04
**Success Criteria** (what must be TRUE):
  1. Screening results display as a formatted rich table showing symbol, price, volume, key metrics, and score
  2. A filter summary shows per-stage elimination counts (universe size, how many removed at each filter stage, final count)
  3. A progress indicator is visible during the screening run so users know the process is active during rate-limited API calls
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md -- Rich results table with 10 columns, compact formatting, color-coded scores, and filter elimination summaries
- [ ] 04-02-PLAN.md -- Progress callback factory and pipeline on_progress integration

### Phase 5: CLI and Integration
**Goal**: Users can run the screener as a standalone command or as part of the strategy workflow, with safe symbol list updates that protect active positions
**Depends on**: Phase 4
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04, OUTP-03, SAFE-03
**Success Criteria** (what must be TRUE):
  1. User can run `run-screener` from the command line and see screening results
  2. User can run `run-strategy --screen` and the screener executes before the strategy
  3. User can pass `--update-symbols` to write screened symbols to config/symbol_list.txt
  4. Running with `--output-only` (the default) displays results without modifying any files
  5. Symbols with active positions (short puts, assigned shares, short calls) are never removed from symbol_list.txt during export
**Plans**: 3 plans

Plans:
- [x] 05-01-PLAN.md -- Typer install, shared CLI helpers (cli_common.py), position-safe symbol export (export.py) with tests
- [x] 05-02-PLAN.md -- Standalone run-screener CLI, run-strategy Typer migration with --screen flag, cli_args.py deletion
- [x] 05-03-PLAN.md -- Gap closure: Add progress callbacks to fetch_universe and fetch_daily_bars (UAT fix)

### Phase 6: Packaging & Tech Debt Cleanup
**Goal**: Fresh `pip install -e .` works without manual dependency installation, CLI shows human-readable config errors, and test suite runs cleanly without environment leaks
**Depends on**: Phase 5
**Requirements**: None (tech debt / integration gap closure)
**Gap Closure**: Closes DEP-TA, DEP-PYYAML, DEP-PYDANTIC, ORPHAN-FMT from v1.0 audit
**Success Criteria** (what must be TRUE):
  1. Running `pip install -e .` in a clean virtualenv installs all required dependencies (ta, pyyaml, pydantic) without errors
  2. Invalid screener.yaml values produce human-readable error messages (not raw Pydantic tracebacks) in both `run-screener` and `run-strategy --screen`
  3. `pytest tests/test_credentials.py` passes regardless of whether `.env` contains real API keys
  4. Stale deferred-items.md is cleaned up or removed
**Plans**: 0 plans

Plans:
- (none yet)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/2 | Complete | 2026-03-08 |
| 2. Data Sources | 1/2 | In Progress|  |
| 3. Screening Pipeline | 0/2 | Not started | - |
| 4. Output and Display | 0/2 | Not started | - |
| 5. CLI and Integration | 3/3 | Complete | 2026-03-10 |
| 6. Packaging & Tech Debt Cleanup | 0/0 | Not started | - |
