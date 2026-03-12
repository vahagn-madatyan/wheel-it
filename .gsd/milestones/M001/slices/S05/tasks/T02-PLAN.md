# T02: 05-cli-and-integration 02

**Slice:** S05 — **Milestone:** M001

## Description

Create the `run-screener` standalone CLI command and migrate `run-strategy` to Typer with the new `--screen` flag.

Purpose: These are the two user-facing entry points for the screener. `run-screener` provides standalone screening with display and optional symbol export. `run-strategy --screen` integrates screening before the existing trading workflow. Both use the shared modules from Plan 01 (cli_common, export).

Output: `scripts/run_screener.py`, updated `scripts/run_strategy.py`, deleted `core/cli_args.py`, updated `pyproject.toml`, test files.

## Must-Haves

- [ ] "User can run `run-screener` from the command line and see screening results"
- [ ] "User can run `run-screener --update-symbols` to write screened symbols to config/symbol_list.txt"
- [ ] "User can run `run-screener --preset aggressive` to override config preset"
- [ ] "User can run `run-screener --config path/to/custom.yaml` for custom config"
- [ ] "User can run `run-screener --verbose` to see per-filter breakdown"
- [ ] "Default `run-screener` (no flags) displays results without modifying any files"
- [ ] "User can run `run-strategy --screen` and the screener executes before the strategy"
- [ ] "`run-strategy --screen` auto-updates symbol_list.txt with position protection before strategy runs"
- [ ] "All existing `run-strategy` flags still work: --fresh-start, --strat-log, --log-level, --log-to-file"
- [ ] "`run-strategy --screen` with zero results warns and uses existing symbol list"
- [ ] "`run-strategy --screen --fresh-start` works: screen first, then fresh-start with updated list"

## Files

- `scripts/run_screener.py`
- `scripts/run_strategy.py`
- `core/cli_args.py`
- `pyproject.toml`
- `tests/test_cli_screener.py`
- `tests/test_cli_strategy.py`
