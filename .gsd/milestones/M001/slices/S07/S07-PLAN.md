# S07: Pipeline Fix + Preset Overhaul

**Goal:** Fix the three independent killers (avg_volume=2M, None=elimination, D/E percentage mismatch) that produce zero screener results, and overhaul all three presets so conservative/moderate/aggressive produce visibly different survivor counts.
**Demo:** `run-screener --preset moderate` returns ≥1 stock against live market data. Running all three presets produces different result counts and threshold strictness.

## Must-Haves

- Stage 2 filter functions (market_cap, debt_equity, net_margin, sales_growth, sector) return `passed=True` when metric is `None`, with reason indicating neutral pass
- Stage 1 filter functions (price, volume, RSI, SMA200) continue to return `passed=False` on `None` (no bar data = unscreenable)
- Finnhub D/E values > 10 are normalized (divided by 100) in `run_stage_2_filters` before filters run
- `avg_volume_min` differentiated: conservative=1000000, moderate=500000, aggressive=200000
- All three presets differ across fundamentals, technicals, and sector lists
- Conservative preset uses tight thresholds and excludes volatile sectors
- Aggressive preset uses loose thresholds, disables `above_sma200`, excludes no sectors
- All 63+ existing tests pass (with updated None-handling assertions)
- `run-screener --preset moderate` produces ≥1 result against live data

## Proof Level

- This slice proves: integration
- Real runtime required: yes (live Finnhub + Alpaca APIs for final verification)
- Human/UAT required: no (automated test suite + live CLI run)

## Verification

- `pytest tests/test_pipeline.py -v` — all tests pass including updated None-handling assertions and new D/E normalization test
- `run-screener --preset moderate` — produces ≥1 stock result (live data)
- `run-screener --preset conservative` and `run-screener --preset aggressive` — produce different result counts from moderate
- At least one verification check confirms D/E normalization triggers debug log for percentage values

## Observability / Diagnostics

- Runtime signals: `logger.debug("D/E normalization: %s → %s for %s", raw, normalized, symbol)` when conversion triggers in `run_stage_2_filters`
- Inspection surfaces: FilterResult.reason text on each ScreenedStock shows "No data — passing with neutral score" for None metrics; filter breakdown display shows pass counts
- Failure visibility: Each FilterResult carries filter_name, passed, actual_value, threshold, and reason — traceable through display layer
- Redaction constraints: none (no secrets in screening data)

## Integration Closure

- Upstream surfaces consumed: `screener/pipeline.py` (10 filter functions, `run_stage_2_filters`, scoring engine), `screener/finnhub_client.py` (`extract_metric`), `screener/config_loader.py` (`ScreenerConfig`), `config/presets/*.yaml`, `models/screened_stock.py` (`FilterResult`, `ScreenedStock`)
- New wiring introduced in this slice: D/E normalization logic in `run_stage_2_filters` (boundary conversion per D009), updated None-pass behavior in 5 filter functions
- What remains before the milestone is truly usable end-to-end: S08 (HV percentile + earnings), S09 (options chain validation + put premium yield), S10 (covered call screener + strategy integration)

## Tasks

- [x] **T01: Merge scanning-improvements branch and validate test baseline** `est:20m`
  - Why: All S01–S06 screener source code (pipeline, filters, tests, presets) exists only in the `scanning-improvements` branch. Nothing can be edited until it's merged into `gsd/M001/S07`.
  - Files: `screener/*.py`, `tests/test_pipeline.py`, `config/presets/*.yaml`, `models/screened_stock.py`, `pyproject.toml`
  - Do: `git merge scanning-improvements` into current branch, resolve any conflicts in pyproject.toml/.gitignore (docs vs code — should be clean). Run `pytest tests/test_pipeline.py -v` to confirm all 63 tests pass as baseline.
  - Verify: `pytest tests/test_pipeline.py -v` passes all 63 tests; `ls screener/pipeline.py config/presets/moderate.yaml` both exist
  - Done when: All S01–S06 source files are on the working branch and the full test suite passes green

- [x] **T02: Fix None-handling in Stage 2 filters and update tests** `est:30m`
  - Why: Every filter function returns `passed=False` on `None` metrics, eliminating stocks with any missing Finnhub data point. Stage 2 filters (Finnhub-dependent) should tolerate `None` since coverage is patchy. This is one of three root causes of zero results (FIX-03).
  - Files: `screener/pipeline.py`, `tests/test_pipeline.py`
  - Do: Change 5 Stage 2 filter functions (market_cap, debt_equity, net_margin, sales_growth, sector) to return `passed=True` with reason `"No data — passing with neutral score"` when metric is `None`. Update `run_stage_2_filters` no-profile case to pass Finnhub-dependent filters with neutral scores. Update 5 test assertions from `passed is False` to `passed is True` and reason text. Keep Stage 1 filters (price, volume, RSI, SMA200) failing on `None`.
  - Verify: `pytest tests/test_pipeline.py -v` — all tests pass with updated assertions
  - Done when: Stocks with `None` Finnhub metrics pass Stage 2 filters and reach scoring, where `compute_wheel_score` gives them neutral 0.5 (D013)

- [x] **T03: Add D/E normalization, overhaul presets, and verify end-to-end** `est:45m`
  - Why: Finnhub returns D/E as percentage (e.g. 150.0 for 150%) but thresholds are ratios (1.0). All three presets share identical technicals (avg_volume=2M kills 95% of stocks) and empty sector lists. Fixing D/E normalization (FIX-02), differentiating thresholds (FIX-04, PRES-01, PRES-02, PRES-03), and adding sector lists (PRES-04) completes the pipeline fix.
  - Files: `screener/pipeline.py`, `config/presets/conservative.yaml`, `config/presets/moderate.yaml`, `config/presets/aggressive.yaml`, `tests/test_pipeline.py`
  - Do: Add D/E percentage-to-ratio conversion in `run_stage_2_filters` after `extract_metric` (if value > 10, divide by 100, log debug). Add test for normalization. Rewrite all 3 presets with differentiated thresholds: avg_volume (1M/500K/200K), price ranges, RSI limits, SMA200 toggle, sector exclude lists. Run full test suite. Run `run-screener --preset moderate` for live verification.
  - Verify: `pytest tests/test_pipeline.py -v` passes; `run-screener --preset moderate` produces ≥1 result; all three presets produce different result counts
  - Done when: All 8 S07 requirements (FIX-01..04, PRES-01..04) are met and verified

## Files Likely Touched

- `screener/pipeline.py` — None-handling in 5 filter functions, D/E normalization in `run_stage_2_filters`
- `tests/test_pipeline.py` — Updated None assertions, new D/E normalization test
- `config/presets/conservative.yaml` — Tight thresholds, sector exclusions
- `config/presets/moderate.yaml` — Balanced thresholds, minimal exclusions
- `config/presets/aggressive.yaml` — Loose thresholds, no sector restrictions
- `models/screened_stock.py` — Read-only (FilterResult, ScreenedStock)
- `screener/config_loader.py` — Read-only (ScreenerConfig validation)
- `screener/finnhub_client.py` — Read-only (extract_metric)
