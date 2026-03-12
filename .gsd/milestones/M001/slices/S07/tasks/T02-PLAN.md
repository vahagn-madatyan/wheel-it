---
estimated_steps: 5
estimated_files: 2
---

# T02: Fix None-handling in Stage 2 filters and update tests

**Slice:** S07 — Pipeline Fix + Preset Overhaul
**Milestone:** M001

## Description

Every filter function returns `passed=False` when its metric is `None`, silently eliminating any stock missing even one Finnhub data point. Since Finnhub coverage is patchy (especially for smaller-cap stocks), this is one of three root causes of zero results. The fix: Stage 2 filters (Finnhub-dependent: market_cap, debt_equity, net_margin, sales_growth, sector) should return `passed=True` with a neutral-pass reason when the metric is `None`. Stage 1 filters (Alpaca-dependent: price, volume, RSI, SMA200) keep `passed=False` on `None` because missing bar data means the stock genuinely can't be screened. The `run_stage_2_filters` no-profile case also changes from fail-all to pass-with-neutral for the 5 Finnhub-dependent filters. Stocks that pass with `None` metrics reach scoring where `compute_wheel_score` already gives them neutral 0.5 scores (D013).

Addresses requirement: **FIX-03**.

## Steps

1. In `screener/pipeline.py`, update `filter_market_cap` — change the `if stock.market_cap is None` branch from `passed=False` to `passed=True` with `reason="No data — passing with neutral score"`. Keep `actual_value=None` and `threshold=min_cap`.
2. Repeat for `filter_debt_equity`, `filter_net_margin`, `filter_sales_growth`, and `filter_sector` — same pattern: `None` metric → `passed=True`, reason `"No data — passing with neutral score"`. For `filter_sector`, change the `if stock.sector is None` branch.
3. In `run_stage_2_filters`, update the `if not profile` block: change the 5 Finnhub-dependent FilterResults (market_cap, debt_equity, net_margin, sales_growth, sector) from `passed=False` to `passed=True` with reason `"No Finnhub data — passing with neutral score"`. Keep `filter_optionable` as-is (it uses Alpaca data, not Finnhub).
4. In `tests/test_pipeline.py`, update 5 test functions: `test_market_cap_none_fails`, `test_debt_equity_none_fails`, `test_net_margin_none_fails`, `test_sales_growth_none_fails`, `test_sector_none_fails`. For each: change `assert result.passed is False` → `assert result.passed is True` and change `assert "unavailable" in result.reason.lower()` → `assert "no data" in result.reason.lower()`.
5. Run `pytest tests/test_pipeline.py -v` and confirm all tests pass (63 baseline + any net change from assertion updates).

## Must-Haves

- [ ] 5 Stage 2 filters return `passed=True` when metric is `None`
- [ ] 4 Stage 1 filters still return `passed=False` when metric is `None`
- [ ] `run_stage_2_filters` no-profile case passes 5 Finnhub-dependent filters with neutral scores
- [ ] 5 test assertions updated from `passed is False` to `passed is True`
- [ ] All tests pass: `pytest tests/test_pipeline.py -v`

## Verification

- `pytest tests/test_pipeline.py -v` — all tests pass
- `pytest tests/test_pipeline.py -v -k "none"` — all None-related tests pass with updated assertions
- Manual review: Stage 1 `test_price_none_fails`, `test_volume_none_fails`, `test_rsi_none_fails`, `test_sma200_none_fails` still assert `passed is False`

## Observability Impact

- Signals added/changed: FilterResult.reason text changes from "unavailable" to "No data — passing with neutral score" for None metrics — visible in filter breakdown display
- How a future agent inspects this: Check `stock.filter_results` for any FilterResult where `passed=True` and `actual_value is None` — indicates neutral pass
- Failure state exposed: None — this task removes a false-negative failure mode

## Inputs

- `screener/pipeline.py` — 10 filter functions with `passed=False` on `None` (from T01 merge)
- `tests/test_pipeline.py` — 63 tests with `test_*_none_fails` assertions (from T01 merge)

## Expected Output

- `screener/pipeline.py` — 5 Stage 2 filters updated: `None` → `passed=True` with neutral reason; `run_stage_2_filters` no-profile case passes Finnhub-dependent filters
- `tests/test_pipeline.py` — 5 test assertions flipped to match new behavior; all tests green
