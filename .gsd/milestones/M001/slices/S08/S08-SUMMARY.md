---
id: S08
parent: M001
milestone: M001
provides:
  - compute_hv_percentile() — 30-day HV percentile over 252-day lookback from Alpaca daily bars
  - filter_hv_percentile() — FilterResult-pattern filter for HV percentile threshold
  - filter_earnings_proximity() — FilterResult-pattern filter excluding stocks with earnings within N days
  - FinnhubClient.earnings_calendar() and earnings_for_symbol() — Finnhub free-tier earnings API
  - EarningsConfig Pydantic model with earnings_exclusion_days field
  - hv_percentile_min added to TechnicalsConfig
  - hv_percentile, next_earnings_date, days_to_earnings fields on ScreenedStock
  - HV%ile column in Rich results table
  - Both new filters integrated into pipeline (Stage 1 + Stage 1b)
  - Preset YAML files updated with hv_percentile_min and earnings_exclusion_days per preset
requires:
  - slice: S07
    provides: Fixed filter pipeline producing actual results, FilterResult pattern, differentiated preset YAML structure
affects:
  - S09
key_files:
  - screener/pipeline.py
  - screener/finnhub_client.py
  - screener/config_loader.py
  - screener/display.py
  - models/screened_stock.py
  - config/presets/conservative.yaml
  - config/presets/moderate.yaml
  - config/presets/aggressive.yaml
  - tests/test_hv_earnings.py
key_decisions:
  - D029: HV percentile in Stage 1 (cheap — uses existing Alpaca bar data already fetched), earnings proximity as Stage 1b (one Finnhub call per Stage 1 survivor)
  - D030: Earnings boundary is inclusive (days_to_earnings <= exclusion_days → fail), protecting against day-of-earnings option selling
  - D031: None hv_percentile and None earnings data both pass with neutral score, consistent with D028 None-handling pattern
patterns_established:
  - Stage 1b pattern: a lightweight Finnhub call per symbol positioned between cheap Stage 1 and expensive Stage 2
  - EarningsConfig as a new top-level config section alongside fundamentals/technicals/options/sectors
observability_surfaces:
  - Filter breakdown table shows hv_percentile and earnings_proximity removal counts
  - Stage summary panel shows new "Earnings" row between Stage 1 and Stage 2
  - HV%ile column in results table shows computed percentile for each survivor
drill_down_paths:
  - tests/test_hv_earnings.py
duration: 1 unit
verification_result: passed
completed_at: 2026-03-11
---

# S08: HV Rank + Earnings Calendar

**HV percentile ranking and earnings proximity filtering active in the screening pipeline with 47 new tests and 244 total passing**

## What Happened

Added two new pre-filter stages to the screening pipeline: HV percentile ranking and earnings proximity exclusion. Both run before the expensive Stage 2 Finnhub calls, preserving cheap-first ordering.

**HV Percentile (HVPR-01..03):** `compute_hv_percentile()` calculates a rolling series of 30-day HV values over a 252-day lookback, then ranks the current value as a percentile (0–100). Higher percentile = elevated volatility = better premium-selling opportunity. The `filter_hv_percentile()` filter uses this with per-preset thresholds (conservative ≥50, moderate ≥30, aggressive ≥20). The computation reuses existing Alpaca daily bar data already fetched in Step 3 of the pipeline — zero additional API calls.

**Earnings Proximity (EARN-01..03):** `FinnhubClient.earnings_for_symbol()` fetches the next earnings date via Finnhub's free-tier earnings calendar endpoint. `filter_earnings_proximity()` excludes stocks with earnings within the configured threshold (conservative 21 days, moderate 14 days, aggressive 7 days). This runs as "Stage 1b" — after Stage 1 technicals pass but before Stage 2 fundamental data fetch.

**Config/Model/Display Updates:** Added `hv_percentile`, `next_earnings_date`, and `days_to_earnings` fields to `ScreenedStock`. Added `EarningsConfig` Pydantic model and `hv_percentile_min` to `TechnicalsConfig`. Updated all three preset YAML files. Added HV%ile column to the Rich results table and updated filter breakdown/stage summary displays.

Also fixed 5 stale test assertions from S07's preset overhaul that expected pre-differentiation values.

## Verification

- **47 new tests** in `tests/test_hv_earnings.py` covering: `compute_hv_percentile()` math (7 tests), `filter_hv_percentile()` pass/fail/None (6 tests), `filter_earnings_proximity()` boundary logic (8 tests), `FinnhubClient` earnings methods (5 tests), preset YAML values (8 tests), ScreenedStock fields (5 tests), config loader integration (6 tests), Stage 1 integration (2 tests)
- **244 total tests passing** (197 existing + 47 new), zero failures
- Fixed 5 stale config tests from S07 preset overhaul
- All pipeline integration tests updated with `compute_hv_percentile` mock and `earnings_for_symbol` mock

## Requirements Advanced

- HVPR-01 — `compute_hv_percentile()` implemented with 30-day window, 252-day lookback, `filter_hv_percentile()` active in Stage 1
- HVPR-02 — `hv_percentile_min` in preset YAMLs: conservative=50, moderate=30, aggressive=20
- HVPR-03 — HV%ile column added to `render_results_table()` in display.py
- EARN-01 — `filter_earnings_proximity()` excludes stocks with earnings ≤ N days (default 14)
- EARN-02 — `FinnhubClient.earnings_calendar()` and `earnings_for_symbol()` using Finnhub free tier
- EARN-03 — `earnings_exclusion_days` in preset YAMLs: conservative=21, moderate=14, aggressive=7

## Requirements Validated

- HVPR-01 — 7 unit tests prove computation correctness (range [0,100], None on insufficient data, high-vol spike → high percentile, low-vol → low percentile)
- HVPR-02 — 3 preset YAML tests + 1 differentiation test confirm per-preset thresholds
- HVPR-03 — Display test suite passes; HV%ile column added to table with fmt_pct formatting
- EARN-01 — 8 filter tests prove boundary logic (inclusive boundary, 0-day, outside window, None passthrough)
- EARN-02 — 5 FinnhubClient tests prove API call shape, error handling, date parsing
- EARN-03 — 3 preset YAML tests + 1 differentiation test confirm per-preset thresholds

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- S08 plan was empty (no tasks/must-haves specified). Implemented the full S08 scope from the roadmap boundary map and requirements instead.
- Fixed 5 stale S07 test assertions that expected pre-overhaul preset values — these were broken by S07's preset differentiation but not caught before S08 started.

## Known Limitations

- `earnings_for_symbol()` makes one Finnhub API call per Stage 1 survivor. For large universes with many Stage 1 survivors, this could hit the 60 calls/min rate limit. The existing throttle (1.1s interval) applies but may slow down screening significantly.
- Earnings proximity filter only considers earnings within the Finnhub lookahead window (60 days). Stocks with earnings exactly at day 60+ are not detected.
- HV percentile requires ≥253 daily bars (1 year). Recently IPO'd stocks get None percentile and pass with neutral score.

## Follow-ups

- none

## Files Created/Modified

- `screener/pipeline.py` — Added `compute_hv_percentile()`, `filter_hv_percentile()`, `filter_earnings_proximity()`, updated `run_stage_1_filters()` (4→5 filters), added Stage 1b earnings check in orchestrator
- `screener/finnhub_client.py` — Added `earnings_calendar()` and `earnings_for_symbol()` methods
- `screener/config_loader.py` — Added `EarningsConfig` model, `hv_percentile_min` to `TechnicalsConfig`, `earnings` section to `ScreenerConfig`
- `screener/display.py` — Added HV%ile column to results table, `earnings_proximity` to filter breakdown, earnings row to stage summary
- `models/screened_stock.py` — Added `hv_percentile`, `next_earnings_date`, `days_to_earnings` fields
- `config/presets/conservative.yaml` — Added `hv_percentile_min: 50`, `earnings.earnings_exclusion_days: 21`
- `config/presets/moderate.yaml` — Added `hv_percentile_min: 30`, `earnings.earnings_exclusion_days: 14`
- `config/presets/aggressive.yaml` — Added `hv_percentile_min: 20`, `earnings.earnings_exclusion_days: 7`
- `tests/test_hv_earnings.py` — New: 47 tests for all S08 features
- `tests/test_screener_config.py` — Fixed 5 stale assertions to match S07 preset values
- `tests/test_pipeline.py` — Updated Stage 1 filter count (4→5), added `compute_hv_percentile` and `earnings_for_symbol` mocks

## Forward Intelligence

### What the next slice should know
- Earnings proximity filter is Stage 1b — positioned between Stage 1 (Alpaca-based technicals) and Stage 2 (Finnhub fundamentals). S09's options chain validation should be Stage 3, running after all of Stage 1 + 1b + 2 pass.
- The pipeline now passes `finnhub_client` earlier in the loop (for `earnings_for_symbol`), so S09 can similarly use the client without restructuring.
- `ScreenedStock` now has 3 new Optional fields. Any code that constructs test fixtures needs to account for them.

### What's fragile
- Pipeline integration tests now require 4 `@patch` decorators and 4 mock params — adding more patched functions in S09 will make these signatures unwieldy. Consider a test fixture builder pattern.
- `earnings_for_symbol` makes a per-symbol Finnhub call inside the main loop. If S09 adds per-symbol Alpaca options calls too, the loop body will have two rate-limited API call sites.

### Authoritative diagnostics
- `python -m pytest tests/test_hv_earnings.py -v` — fastest way to verify all S08 features work
- Filter breakdown table in `run-screener` output shows `hv_percentile` and `earnings_proximity` removal counts

### What assumptions changed
- Originally assumed S08 plan would have tasks defined — it was empty. Built directly from roadmap boundary map and requirements.
