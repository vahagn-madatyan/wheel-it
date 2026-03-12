# T01: 02-data-sources 01

**Slice:** S02 — **Milestone:** M001

## Description

Build a rate-limited Finnhub API client that fetches company profile and basic financials, handles 429 errors with retry/skip logic, and extracts metric values through fallback key chains for missing data resilience.

Purpose: This is the fundamental data source for the screener. Without rate limiting, 200+ symbol screening trips 429 errors. Without fallback chains, undocumented Finnhub metric key names cause silent None propagation.

Output: `screener/finnhub_client.py` with FinnhubClient class, metric fallback chains, and extraction helpers. Full test suite covering rate limiting, retry, fallback chains, and empty response handling.

## Must-Haves

- [ ] "Finnhub API calls are throttled to at most ~60 calls/min via sleep-based rate limiting"
- [ ] "A 429 response triggers one retry after 5s backoff; a second 429 skips the symbol without crashing"
- [ ] "Missing/null metric values are resolved via fallback key chains (try primary key, then alternates)"
- [ ] "Completely empty Finnhub responses (symbol not found) are logged as WARNING and skipped"
- [ ] "Each API call is logged at DEBUG level with symbol, endpoint, and response time"

## Files

- `screener/finnhub_client.py`
- `tests/test_finnhub_client.py`
- `pyproject.toml`
