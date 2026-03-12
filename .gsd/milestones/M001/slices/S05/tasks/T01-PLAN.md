# T01: 05-cli-and-integration 01

**Slice:** S05 — **Milestone:** M001

## Description

Create the symbol export module with position-safe merge logic and the shared CLI helpers that both `run-screener` and `run-strategy` will use.

Purpose: The export module is the core safety mechanism -- it ensures active wheel positions are never removed from the symbol list when updating with screener results. The CLI common module extracts shared credential validation used by both entry points. These must exist before the CLI entry points are wired in Plan 02.

Output: `screener/export.py`, `core/cli_common.py`, `tests/test_export.py`, updated `pyproject.toml` with typer dependency.

## Must-Haves

- [ ] "Screened symbols can be written to config/symbol_list.txt via export function"
- [ ] "Symbols with active positions (short puts, assigned shares, short calls) are never removed from symbol_list.txt"
- [ ] "A colored diff is displayed showing added, removed, and protected symbols before writing"
- [ ] "Zero screener results skips file write and prints warning"
- [ ] "Missing Alpaca credentials produce a hard error before any export attempt"

## Files

- `pyproject.toml`
- `core/cli_common.py`
- `screener/export.py`
- `tests/test_export.py`
