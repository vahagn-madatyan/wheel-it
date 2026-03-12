---
estimated_steps: 7
estimated_files: 5
---

# T03: Add D/E normalization, overhaul presets, and verify end-to-end

**Slice:** S07 — Pipeline Fix + Preset Overhaul
**Milestone:** M001

## Description

Two remaining root causes: (1) Finnhub returns `totalDebtToEquity` as a percentage (e.g. 150.0 for 150% D/E) but preset thresholds use ratio format (e.g. 1.0), so even conservatively-leveraged companies fail; (2) all three presets share identical technicals (`avg_volume_min: 2000000` kills ~95% of the universe) and empty sector lists — no differentiation.

This task adds D/E percentage-to-ratio normalization at the boundary (D009) in `run_stage_2_filters`, then rewrites all three preset YAMLs with differentiated thresholds across fundamentals, technicals, and sectors. Final verification runs `run-screener` against live data to confirm the pipeline produces results.

Addresses requirements: **FIX-01**, **FIX-02**, **FIX-04**, **PRES-01**, **PRES-02**, **PRES-03**, **PRES-04**.

## Steps

1. In `screener/pipeline.py:run_stage_2_filters`, after the `stock.debt_equity = extract_metric(metrics, "debt_equity")` line, add normalization: if `stock.debt_equity is not None and stock.debt_equity > 10`, divide by 100. Log a debug message: `"D/E normalization: %.2f → %.2f for %s"`. This is the boundary conversion point per D009 — keep `extract_metric` and `filter_debt_equity` pure.
2. Add a test in `tests/test_pipeline.py` for D/E normalization: create a test that calls the normalization logic directly or tests `filter_debt_equity` with a pre-normalized value to verify the conversion path works. Specifically: test that a stock with `debt_equity=150.0` (Finnhub percentage format) would be normalized to `1.5` before filtering against `debt_equity_max=2.0` and pass. Also test that a value of `0.8` (already a ratio) is not modified.
3. Rewrite `config/presets/conservative.yaml`: fundamentals (market_cap_min=10000000000, debt_equity_max=0.5, net_margin_min=10, sales_growth_min=10), technicals (price_min=20, price_max=100, avg_volume_min=1000000, rsi_max=55, above_sma200=true), sectors exclude=["Biotechnology", "Cannabis", "Oil & Gas Exploration & Production"]. Use plain integers only (D002).
4. Rewrite `config/presets/moderate.yaml`: fundamentals (market_cap_min=2000000000, debt_equity_max=1.5, net_margin_min=0, sales_growth_min=5), technicals (price_min=10, price_max=200, avg_volume_min=500000, rsi_max=65, above_sma200=true), sectors exclude=["Cannabis"]. Use plain integers only (D002).
5. Rewrite `config/presets/aggressive.yaml`: fundamentals (market_cap_min=500000000, debt_equity_max=3.0, net_margin_min=-10, sales_growth_min=-5), technicals (price_min=5, price_max=500, avg_volume_min=200000, rsi_max=75, above_sma200=false), sectors exclude=[] (empty — no restrictions). Use plain integers only (D002).
6. Run `pytest tests/test_pipeline.py -v` and confirm all tests pass including the new D/E normalization test.
7. Run `run-screener --preset moderate`, then `--preset conservative`, then `--preset aggressive`. Confirm: moderate produces ≥1 result; all three produce different result counts. If run during market hours, results should be non-zero for at least moderate and aggressive.

## Must-Haves

- [ ] D/E normalization in `run_stage_2_filters`: values > 10 divided by 100 with debug log
- [ ] D/E normalization test covers both percentage (>10) and ratio (<10) inputs
- [ ] `conservative.yaml`: avg_volume_min=1000000, tight fundamentals, sector excludes populated
- [ ] `moderate.yaml`: avg_volume_min=500000, balanced fundamentals, minimal sector excludes
- [ ] `aggressive.yaml`: avg_volume_min=200000, loose fundamentals, above_sma200=false, no sector excludes
- [ ] All three presets differ across fundamentals, technicals, and sectors sections (PRES-01)
- [ ] `pytest tests/test_pipeline.py -v` — all tests pass
- [ ] `run-screener --preset moderate` — produces ≥1 result (live data)

## Verification

- `pytest tests/test_pipeline.py -v` — all tests pass including D/E normalization test
- `diff config/presets/conservative.yaml config/presets/moderate.yaml` — shows differences in every section
- `diff config/presets/moderate.yaml config/presets/aggressive.yaml` — shows differences in every section
- `run-screener --preset moderate` — produces ≥1 result line in output
- `run-screener --preset conservative` and `run-screener --preset aggressive` — produce different result counts from moderate

## Observability Impact

- Signals added/changed: `logger.debug("D/E normalization: %.2f → %.2f for %s", raw, normalized, symbol)` when Finnhub percentage value is converted to ratio
- How a future agent inspects this: Run `run-screener --log-level DEBUG` and grep for "D/E normalization" to see which stocks triggered conversion
- Failure state exposed: If D/E normalization wrongly triggers (value < 10 but looks like percentage), the debug log shows the before/after for diagnosis

## Inputs

- `screener/pipeline.py` — Stage 2 filters with None-tolerance (from T02)
- `tests/test_pipeline.py` — Updated test suite (from T02)
- `config/presets/*.yaml` — Current identical-technicals presets (from T01 merge)
- `screener/config_loader.py` — `ScreenerConfig` with `debt_equity_max ≤ 10` validator (read-only)

## Expected Output

- `screener/pipeline.py` — D/E normalization added in `run_stage_2_filters` after `extract_metric` call
- `tests/test_pipeline.py` — New D/E normalization test function(s)
- `config/presets/conservative.yaml` — Fully differentiated tight preset with sector exclusions
- `config/presets/moderate.yaml` — Fully differentiated balanced preset
- `config/presets/aggressive.yaml` — Fully differentiated loose preset with `above_sma200: false`
- Live verification: `run-screener --preset moderate` shows stock results in terminal
