# S05: Cli And Integration

**Goal:** Create the symbol export module with position-safe merge logic and the shared CLI helpers that both `run-screener` and `run-strategy` will use.
**Demo:** Create the symbol export module with position-safe merge logic and the shared CLI helpers that both `run-screener` and `run-strategy` will use.

## Must-Haves


## Tasks

- [x] **T01: 05-cli-and-integration 01** `est:3min`
  - Create the symbol export module with position-safe merge logic and the shared CLI helpers that both `run-screener` and `run-strategy` will use.

Purpose: The export module is the core safety mechanism -- it ensures active wheel positions are never removed from the symbol list when updating with screener results. The CLI common module extracts shared credential validation used by both entry points. These must exist before the CLI entry points are wired in Plan 02.

Output: `screener/export.py`, `core/cli_common.py`, `tests/test_export.py`, updated `pyproject.toml` with typer dependency.
- [x] **T02: 05-cli-and-integration 02** `est:4min`
  - Create the `run-screener` standalone CLI command and migrate `run-strategy` to Typer with the new `--screen` flag.

Purpose: These are the two user-facing entry points for the screener. `run-screener` provides standalone screening with display and optional symbol export. `run-strategy --screen` integrates screening before the existing trading workflow. Both use the shared modules from Plan 01 (cli_common, export).

Output: `scripts/run_screener.py`, updated `scripts/run_strategy.py`, deleted `core/cli_args.py`, updated `pyproject.toml`, test files.
- [x] **T03: 05-cli-and-integration 03** `est:3min`
  - Fix the blank screen during `run-screener` by adding progress callbacks to the two long-running fetch operations that currently execute silently: `fetch_universe()` (2 API calls) and `fetch_daily_bars()` (batched across the entire symbol universe).

Purpose: UAT Test 1 failed because the user saw a blank screen — the Rich progress bar context was active but no progress tasks were created until after all data had already been fetched. This blocks Tests 2-4 and 6.

Output: Both fetch operations now fire progress callbacks so the user sees animated progress from the moment the pipeline starts.

## Files Likely Touched

- `pyproject.toml`
- `core/cli_common.py`
- `screener/export.py`
- `tests/test_export.py`
- `scripts/run_screener.py`
- `scripts/run_strategy.py`
- `core/cli_args.py`
- `pyproject.toml`
- `tests/test_cli_screener.py`
- `tests/test_cli_strategy.py`
- `screener/market_data.py`
- `screener/pipeline.py`
