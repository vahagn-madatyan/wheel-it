# T02: 02-data-sources 02

**Slice:** S02 — **Milestone:** M001

## Description

Build an Alpaca market data module that fetches daily bars in batches and computes RSI(14) and SMA(200) technical indicators using the ta library, handling insufficient data and NaN values gracefully.

Purpose: Technical indicators are required for Phase 3 screening filters (RSI overbought check, price-above-SMA200 trend filter). Correct computation requires split-adjusted bars, proper NaN handling, and sufficient history validation.

Output: `screener/market_data.py` with fetch_daily_bars and compute_indicators functions. Full test suite covering indicator math, edge cases (insufficient bars, NaN), and batch fetching.

## Must-Haves

- [ ] "RSI(14) is computed correctly from Alpaca daily bar close prices using ta library"
- [ ] "SMA(200) is computed correctly from Alpaca daily bar close prices using ta library"
- [ ] "Symbols with fewer than 200 bars return sma_200=None and above_sma200=None"
- [ ] "Symbols with fewer than 30 bars return rsi_14=None"
- [ ] "NaN values from ta library are converted to None (not propagated as float NaN)"
- [ ] "Alpaca bars are fetched in batches of ~20 symbols with split adjustment and no limit parameter"
- [ ] "Average daily volume is computed from the fetched bar data"

## Files

- `screener/market_data.py`
- `tests/test_market_data.py`
