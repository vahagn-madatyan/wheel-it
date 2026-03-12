# S02: Data Sources

**Goal:** Build a rate-limited Finnhub API client that fetches company profile and basic financials, handles 429 errors with retry/skip logic, and extracts metric values through fallback key chains for missing data resilience.
**Demo:** Build a rate-limited Finnhub API client that fetches company profile and basic financials, handles 429 errors with retry/skip logic, and extracts metric values through fallback key chains for missing data resilience.

## Must-Haves


## Tasks

- [x] **T01: 02-data-sources 01** `est:4min`
  - Build a rate-limited Finnhub API client that fetches company profile and basic financials, handles 429 errors with retry/skip logic, and extracts metric values through fallback key chains for missing data resilience.

Purpose: This is the fundamental data source for the screener. Without rate limiting, 200+ symbol screening trips 429 errors. Without fallback chains, undocumented Finnhub metric key names cause silent None propagation.

Output: `screener/finnhub_client.py` with FinnhubClient class, metric fallback chains, and extraction helpers. Full test suite covering rate limiting, retry, fallback chains, and empty response handling.
- [x] **T02: 02-data-sources 02** `est:3min`
  - Build an Alpaca market data module that fetches daily bars in batches and computes RSI(14) and SMA(200) technical indicators using the ta library, handling insufficient data and NaN values gracefully.

Purpose: Technical indicators are required for Phase 3 screening filters (RSI overbought check, price-above-SMA200 trend filter). Correct computation requires split-adjusted bars, proper NaN handling, and sufficient history validation.

Output: `screener/market_data.py` with fetch_daily_bars and compute_indicators functions. Full test suite covering indicator math, edge cases (insufficient bars, NaN), and batch fetching.

## Files Likely Touched

- `screener/finnhub_client.py`
- `tests/test_finnhub_client.py`
- `pyproject.toml`
- `screener/market_data.py`
- `tests/test_market_data.py`
