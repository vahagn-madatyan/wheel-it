# T03: 05-cli-and-integration 03

**Slice:** S05 — **Milestone:** M001

## Description

Fix the blank screen during `run-screener` by adding progress callbacks to the two long-running fetch operations that currently execute silently: `fetch_universe()` (2 API calls) and `fetch_daily_bars()` (batched across the entire symbol universe).

Purpose: UAT Test 1 failed because the user saw a blank screen — the Rich progress bar context was active but no progress tasks were created until after all data had already been fetched. This blocks Tests 2-4 and 6.

Output: Both fetch operations now fire progress callbacks so the user sees animated progress from the moment the pipeline starts.

## Must-Haves

- [ ] "User sees animated progress during universe fetch (2 API calls)"
- [ ] "User sees a progress bar advancing per batch during daily bar fetching"
- [ ] "The screen is never blank/frozen during long-running API operations"

## Files

- `screener/market_data.py`
- `screener/pipeline.py`
