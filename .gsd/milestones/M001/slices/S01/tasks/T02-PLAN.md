# T02: 01-foundation 02

**Slice:** S01 — **Milestone:** M001

## Description

Add Finnhub API key loading to the existing credentials module with a hard-error helper function.

Purpose: Ensure the screener can access the Finnhub API key from .env with a clear error message if it's missing, following the existing credentials.py pattern.
Output: Extended credentials.py with FINNHUB_API_KEY and require_finnhub_key(), plus tests.

## Must-Haves

- [ ] "Adding FINNHUB_API_KEY to .env makes it available to the screener without code changes"
- [ ] "Missing FINNHUB_API_KEY produces a hard error with clear instructions including the signup URL"

## Files

- `config/credentials.py`
- `tests/test_credentials.py`
