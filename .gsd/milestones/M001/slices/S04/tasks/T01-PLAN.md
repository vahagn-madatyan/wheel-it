# T01: 04-output-and-display 01

**Slice:** S04 — **Milestone:** M001

## Description

Create the screener display module with Rich-formatted results table and filter elimination summaries.

Purpose: Users need clear, informative terminal output from the screening pipeline -- a formatted table showing all passing stocks ranked by score, and a funnel summary showing how many stocks were eliminated at each filtering stage.

Output: `screener/display.py` with three rendering functions (results table, stage summary panel, per-filter breakdown table), number formatting helpers, and comprehensive tests.

## Must-Haves

- [ ] "Screening results display as a formatted rich table with 10 columns: Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, Score, Sector"
- [ ] "Table rows are numbered and sorted by score descending"
- [ ] "Scores are color-coded green/yellow/red based on thirds of the actual score distribution"
- [ ] "Numbers are compactly formatted: market cap as $2.1B, volume as 3.2M, price as $24.50, percentages with 1 decimal"
- [ ] "A stage summary panel shows counts at each stage: Universe, After bars, Stage 1, Stage 2, Scored"
- [ ] "A per-filter breakdown table shows a waterfall of each filter's removal count and remaining count"
- [ ] "Zero passing stocks shows a message instead of crashing"

## Files

- `pyproject.toml`
- `screener/display.py`
- `tests/test_display.py`
