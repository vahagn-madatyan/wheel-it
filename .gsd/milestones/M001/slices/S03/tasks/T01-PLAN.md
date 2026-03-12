# T01: 03-screening-pipeline 01

**Slice:** S03 — **Milestone:** M001

## Description

Implement all 10 screening filter functions, historical volatility computation, and add the hv_30 field to ScreenedStock.

Purpose: These pure filter functions are the core logic of the screening pipeline. Each takes a ScreenedStock + config (and optionally external data), returns a FilterResult, and handles None/missing data gracefully. This plan creates the building blocks that Plan 02 will orchestrate.

Output: screener/pipeline.py with 10 filter functions + HV computation + stage runner helpers, updated ScreenedStock model, comprehensive tests.

## Must-Haves

- [ ] "Stocks below market cap minimum are excluded with a FilterResult recording the failure"
- [ ] "Stocks above debt/equity maximum are excluded with a FilterResult"
- [ ] "Stocks below net margin minimum are excluded with a FilterResult"
- [ ] "Stocks below sales growth minimum are excluded with a FilterResult"
- [ ] "Stocks outside price range are excluded with a FilterResult"
- [ ] "Stocks below volume minimum are excluded with a FilterResult"
- [ ] "Stocks with RSI above maximum are excluded with a FilterResult"
- [ ] "Stocks below SMA(200) are excluded with a FilterResult"
- [ ] "Non-optionable stocks are excluded with a FilterResult"
- [ ] "Stocks in excluded sectors are excluded with a FilterResult"
- [ ] "Each filter handles None/missing data by failing the stock with an explanatory reason"
- [ ] "Historical volatility can be computed from daily bar data for use in scoring"

## Files

- `models/screened_stock.py`
- `screener/pipeline.py`
- `tests/test_pipeline.py`
