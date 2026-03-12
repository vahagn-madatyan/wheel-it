# S04: Output And Display

**Goal:** Create the screener display module with Rich-formatted results table and filter elimination summaries.
**Demo:** Create the screener display module with Rich-formatted results table and filter elimination summaries.

## Must-Haves


## Tasks

- [x] **T01: 04-output-and-display 01** `est:3min`
  - Create the screener display module with Rich-formatted results table and filter elimination summaries.

Purpose: Users need clear, informative terminal output from the screening pipeline -- a formatted table showing all passing stocks ranked by score, and a funnel summary showing how many stocks were eliminated at each filtering stage.

Output: `screener/display.py` with three rendering functions (results table, stage summary panel, per-filter breakdown table), number formatting helpers, and comprehensive tests.
- [x] **T02: 04-output-and-display 02** `est:3min`
  - Add progress indicator support to the screening pipeline with a Rich-based callback factory.

Purpose: Screening 200+ symbols with rate-limited Finnhub calls takes minutes. Users need visual feedback that the process is active, with per-stage progress bars showing which stage is running and how far along it is. The Finnhub stage (slowest at ~1s/symbol) shows the current symbol name.

Output: `progress_context()` factory in display.py that yields a callback, and `on_progress` parameter added to `run_pipeline()` with callback calls at each stage boundary.

## Files Likely Touched

- `pyproject.toml`
- `screener/display.py`
- `tests/test_display.py`
- `screener/display.py`
- `screener/pipeline.py`
- `tests/test_display.py`
- `tests/test_pipeline.py`
