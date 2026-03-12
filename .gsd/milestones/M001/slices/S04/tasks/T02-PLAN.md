# T02: 04-output-and-display 02

**Slice:** S04 — **Milestone:** M001

## Description

Add progress indicator support to the screening pipeline with a Rich-based callback factory.

Purpose: Screening 200+ symbols with rate-limited Finnhub calls takes minutes. Users need visual feedback that the process is active, with per-stage progress bars showing which stage is running and how far along it is. The Finnhub stage (slowest at ~1s/symbol) shows the current symbol name.

Output: `progress_context()` factory in display.py that yields a callback, and `on_progress` parameter added to `run_pipeline()` with callback calls at each stage boundary.

## Must-Haves

- [ ] "A progress indicator is visible during the screening run so users know the process is active"
- [ ] "Progress shows per-stage bars: Fetching Alpaca bars, Filtering Stage 1, Fetching Finnhub data, Filtering Stage 2, Scoring"
- [ ] "Finnhub stage shows current symbol name alongside the progress bar"
- [ ] "Pipeline remains fully testable without Rich -- on_progress callback is optional"

## Files

- `screener/display.py`
- `screener/pipeline.py`
- `tests/test_display.py`
- `tests/test_pipeline.py`
