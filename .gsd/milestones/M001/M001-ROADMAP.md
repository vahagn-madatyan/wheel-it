# M001: Screener Fix + Covered Calls

**Vision:** Fix the broken stock screening pipeline (zero results from all presets), add HV percentile ranking and earnings calendar filtering as new pre-filter stages, add options chain liquidity validation, and introduce covered call screening for the wheel strategy's second leg — so the user has a fully functional put screener AND call screener working end-to-end through the CLI and strategy bot.

## Success Criteria

- Running `run-screener --preset moderate` against live market data produces at least one stock result
- Running the screener with conservative, moderate, and aggressive presets produces noticeably different survivor counts and score distributions
- Each preset enforces different thresholds across ALL filter categories (fundamentals, technicals, options, earnings) and includes sector avoid/prefer lists
- Stocks with missing Finnhub data (None values) appear in results with neutral scores instead of being silently eliminated
- HV Percentile column appears in screener results with values between 0–100 for each surviving stock
- Stocks with earnings within the configured threshold (default 14 days) are excluded from results
- Only stocks with tradeable options (OI above threshold, bid/ask spread below threshold) survive to final results
- Annualized put premium yield is displayed in the screener results table for each passing stock
- Running `run-call-screener` with a symbol and cost basis produces a Rich table of covered call recommendations with strike ≥ cost basis
- Running `run-strategy` on assigned stock positions automatically selects covered calls using the call screener logic

## Key Risks / Unknowns

- Zero-results pipeline bug root cause — might be Finnhub debt/equity data format (percentage vs ratio), overly aggressive thresholds (avg_volume at 2M kills 10K+ stocks), or both acting together
- Finnhub earnings calendar free tier — rate limit interaction with existing 60 calls/min budget, possible data gaps for small-cap stocks
- Alpaca options chain data shape — OI and bid/ask spread availability for the nearest ATM put may vary by underlying

## Proof Strategy

- Zero-results bug → retire in S07 by running `run-screener --preset moderate` against live market data and getting non-zero results
- Earnings API reliability → retire in S08 by fetching earnings data for screener survivors and verifying filter exclusion works
- Options chain data availability → retire in S09 by running the full pipeline through options chain validation and displaying put premium yield

## Verification Classes

- Contract verification: pytest test suite (193+ tests from v1.0, extended per slice), filter function unit tests, scoring math tests
- Integration verification: `run-screener` end-to-end against live Alpaca + Finnhub APIs with each preset
- Operational verification: none (batch CLI tool, no long-running service)
- UAT / human verification: user runs each preset and confirms results are reasonable; user runs `run-call-screener` on an assigned position

## Milestone Definition of Done

This milestone is complete only when all are true:

- `run-screener --preset moderate` produces non-zero results against live market data
- All three presets produce visibly different result counts, score distributions, and sector coverage
- HV Percentile and earnings proximity filtering are active in the pipeline
- Options chain OI and bid/ask spread filtering eliminates illiquid options
- Put premium annualized yield appears in the screener results table
- `run-call-screener` produces covered call recommendations for a given symbol + cost basis
- `run-strategy` integrates call screener for assigned positions
- All success criteria are re-checked against live behavior, not just test fixtures

## Requirement Coverage

- Covers: FIX-01, FIX-02, FIX-03, FIX-04, PRES-01, PRES-02, PRES-03, PRES-04, HVPR-01, HVPR-02, HVPR-03, EARN-01, EARN-02, EARN-03, OPTS-01, OPTS-02, OPTS-03, OPTS-04, OPTS-05, CALL-01, CALL-02, CALL-03, CALL-04, CALL-05, CALL-06
- Partially covers: none
- Leaves for later: none
- Orphan risks: none — all 25 active requirements have primary slice ownership

## Slices

- [x] **S01: Foundation** `risk:medium` `depends:[]`
  > After this: User can configure screening criteria through YAML config files with preset profiles, and the system validates all configuration with clear Pydantic error messages.

- [x] **S02: Data Sources** `risk:medium` `depends:[S01]`
  > After this: Screener fetches fundamental data from Finnhub with rate limiting and computes RSI/SMA200 from Alpaca daily bars, handling missing data gracefully.

- [x] **S03: Screening Pipeline** `risk:medium` `depends:[S02]`
  > After this: 10 screening filters run in cheap-first order, scoring engine ranks survivors by wheel suitability, and pipeline orchestrator ties it all together.

- [x] **S04: Output and Display** `risk:medium` `depends:[S03]`
  > After this: Screening results display as a Rich table with color-coded scores, filter elimination summaries show what was removed at each stage, and progress indicators are visible during rate-limited API calls.

- [x] **S05: CLI and Integration** `risk:medium` `depends:[S04]`
  > After this: User runs `run-screener` as standalone CLI, `run-strategy --screen` runs screener before strategy, and `--update-symbols` safely exports symbols without removing active positions.

- [x] **S06: Packaging Cleanup** `risk:medium` `depends:[S05]`
  > After this: Fresh `pip install -e .` works without manual dep installs, CLI shows Rich Panel config errors, credential tests pass regardless of local .env contents.

- [ ] **S07: Pipeline Fix + Preset Overhaul** `risk:high` `depends:[S06]`
  > After this: User runs `run-screener --preset moderate` and gets actual stock results. Each of the three presets produces different survivor counts with visibly different threshold strictness. Stocks with missing Finnhub data survive with neutral scores instead of being eliminated.

- [ ] **S08: HV Rank + Earnings Calendar** `risk:medium` `depends:[S07]`
  > After this: User runs `run-screener` and sees an HV Percentile column (0–100) in the results table. Stocks with earnings within the configured threshold are excluded. Both filters run before options chain API calls (cheap-first ordering preserved).

- [ ] **S09: Options Chain Validation** `risk:medium` `depends:[S08]`
  > After this: User runs `run-screener` and only sees stocks with liquid, tradeable options — low OI and wide spread stocks are eliminated. An annualized put premium yield column appears in the results table.

- [ ] **S10: Covered Call Screening + Strategy Integration** `risk:medium` `depends:[S09]`
  > After this: User runs `run-call-screener AAPL --cost-basis 175` and gets a Rich table of recommended covered calls (strike ≥ cost basis). Running `run-strategy` on assigned positions automatically selects covered calls using the same logic.

## Boundary Map

### S06 → S07

Produces (already shipped):
- `screener/pipeline.py` → `run_pipeline()` orchestrator with 3-stage flow (universe → filter → score)
- `screener/pipeline.py` → 10 filter functions (`filter_market_cap`, `filter_debt_equity`, `filter_avg_volume`, etc.) returning `FilterResult`
- `screener/finnhub_client.py` → `FinnhubClient` with `company_metrics()`, `company_profile()`, rate limiting, fallback key chains
- `screener/config_loader.py` → `load_config()` with preset resolution, Pydantic validation
- `config/presets/*.yaml` → conservative, moderate, aggressive preset files
- `models/screened_stock.py` → `ScreenedStock` dataclass with all screening fields

Consumes: nothing (this is the existing v1.0 foundation)

### S07 → S08

Produces:
- Fixed `filter_debt_equity()` with correct Finnhub value normalization (percentage-to-ratio if needed)
- All filter functions updated to pass stocks with `None` metric values (neutral score, not elimination)
- Differentiated `config/presets/*.yaml` with per-category threshold differences and `sector_avoid`/`sector_prefer` lists
- `avg_volume_min` differentiated: conservative=1M, moderate=500K, aggressive=200K
- Verified: `run-screener --preset moderate` returns ≥1 stock against live data

Consumes from S06:
- `screener/pipeline.py` → existing filter functions and `FilterResult` pattern
- `screener/finnhub_client.py` → `company_metrics()` returning raw Finnhub values
- `config/presets/*.yaml` → existing preset structure

### S08 → S09

Produces:
- `hv_percentile` field on `ScreenedStock` + `compute_hv_percentile()` function (30-day HV percentile over 252-day lookback using Alpaca daily bars)
- `filter_hv_percentile()` — new filter function using `FilterResult` pattern
- `filter_earnings_proximity()` — new filter function excluding stocks with earnings within N days
- `FinnhubClient.earnings_calendar()` — new method fetching upcoming earnings via Finnhub free tier
- Updated `config/presets/*.yaml` with `hv_percentile_min` (conservative≥50, moderate≥30, aggressive≥20) and `earnings_exclusion_days` (conservative≥21, moderate≥14, aggressive≥7)
- HV Percentile column added to `screener/display.py` Rich results table
- Both new filters inserted into pipeline before any per-symbol options chain calls

Consumes from S07:
- Fixed filter pipeline producing actual results
- `FilterResult` pattern and pipeline stage insertion points
- Differentiated preset YAML structure

### S09 → S10

Produces:
- `filter_options_oi()` — filter function checking OI on nearest ATM put via Alpaca options API
- `filter_options_spread()` — filter function checking bid/ask spread on nearest ATM put
- `compute_put_premium_yield()` — annualized yield computation from best put premium
- Options chain validation stage in pipeline (runs after all fundamental/technical/HV/earnings filters pass)
- Updated `config/presets/*.yaml` with `options_oi_min` and `options_spread_max` per preset
- `put_premium_yield` column added to `screener/display.py` Rich results table

Consumes from S08:
- HV percentile + earnings filters running in pipeline as pre-filter stages
- Preset YAML structure with per-category thresholds
- `FinnhubClient` and `BrokerClient` for API access patterns

### S10 (terminal slice)

Produces:
- `screener/call_screener.py` — call screening logic: fetch OTM calls for symbol, filter by DTE/OI/spread/delta, enforce strike ≥ cost basis, rank by annualized return
- `scripts/run_call_screener.py` → Typer CLI entry point registered as `run-call-screener` in pyproject.toml
- Rich table output: symbol, cost basis, recommended strike, DTE, premium, delta, annualized return
- Integration in `scripts/run_strategy.py` → when state is `long_shares`, call screener selects the best covered call
- Reuses preset-based DTE/OI/spread/delta thresholds from put screening infrastructure

Consumes from S09:
- Options chain API integration patterns (OI/spread filtering)
- Preset YAML structure with options-related thresholds
- `BrokerClient` for Alpaca options API access
- `core/state_manager.py` → `update_state()` for detecting assigned positions
