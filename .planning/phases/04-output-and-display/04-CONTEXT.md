# Phase 4: Output and Display - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Rich table rendering of screening results, filter elimination summary (stage funnel + per-filter breakdown), and progress indicator during pipeline execution. No CLI entry points, no symbol export, no --verbose flag wiring -- those are Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Results Table Layout
- 10 columns: Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, Score, Sector
- Compact number formatting: market cap as $2.1B, volume as 3.2M, price as $24.50, percentages with 1 decimal
- Show ALL passing stocks (no top-N cap), numbered rows, sorted by score descending
- Color-coded scores: green for top-third, yellow for middle-third, red for bottom-third
- Rich Table with styled headers

### Filter Elimination Summary
- **Two rendering functions built in Phase 4:**
  - `render_stage_summary()` -- compact Rich Panel showing Universe → Stage 1 → Stage 2 → Scored with counts
  - `render_filter_breakdown()` -- per-filter table showing each of 10 filters with stocks removed and remaining count
- Phase 5 wires --verbose flag to select between them (stage summary default, per-filter for verbose)
- Both use Rich formatting (Panel for stage summary, Table for per-filter breakdown)

### Progress Indicator
- Per-stage Rich progress bars via callback injection into run_pipeline()
- Stages shown: Fetching Alpaca bars, Filtering Stage 1, Fetching Finnhub data, Filtering Stage 2, Scoring
- Finnhub stage shows current symbol name alongside the progress bar (e.g., "MSFT")
- Progress callback is optional parameter on run_pipeline() -- pipeline stays testable without Rich dependency
- Callback signature: on_progress(stage, current, total, symbol=None)

### Output Integration
- New module: `screener/display.py`
- Pipeline returns data only (list[ScreenedStock]) -- caller handles display
- Display functions accept optional `Console` parameter (defaults to global Console) for testability
- Progress callback provided by the display module, passed into pipeline by the CLI caller (Phase 5)
- Rich library added as project dependency in pyproject.toml

### Claude's Discretion
- Exact Rich Table styling (border style, padding, header colors)
- Progress bar column layout and refresh rate
- How to handle edge cases (0 passing stocks, very long sector names, None values in table cells)
- Internal helper functions for number formatting

</decisions>

<specifics>
## Specific Ideas

- Stage summary panel styled like the Rich Panel preview: bordered box with aligned counts and percentage reductions
- Finnhub progress bar is the most important one since it's the slowest stage (~1s/symbol with rate limiting)
- Score color thresholds based on thirds of the actual score distribution (not fixed cutoffs)
- Per-filter breakdown shows a waterfall: each row subtracts from previous remaining count

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `models/screened_stock.py`: ScreenedStock with all 12+ fields + FilterResult tracking + `passed_all_filters` and `failed_filters` properties -- display reads these directly
- `screener/pipeline.py`: `run_pipeline()` returns list[ScreenedStock] with all filter results populated -- the exact data source for display
- `FilterResult` dataclass has `filter_name`, `passed`, `actual_value`, `threshold`, `reason` -- enough for per-filter breakdown

### Established Patterns
- `import logging as stdlib_logging` to avoid logging/ shadow -- display.py must follow this
- No existing print() statements in codebase -- all output via logging currently
- Screener modules live in `screener/` package with relative imports

### Integration Points
- `screener/display.py` -- new module alongside pipeline.py, config_loader.py
- `run_pipeline()` needs optional `on_progress` callback parameter added
- `pyproject.toml` needs `rich` dependency added
- Phase 5 CLI caller will import display functions and wire them to pipeline output

</code_context>

<deferred>
## Deferred Ideas

- --verbose flag wiring to select stage summary vs per-filter breakdown -- Phase 5 CLI integration
- v2 OUTP-05: Options chain preview alongside each result (best put strike, premium, delta)
- v2 OUTP-06: --dry-run mode showing what would change in symbol_list.txt

</deferred>

---

*Phase: 04-output-and-display*
*Context gathered: 2026-03-08*
