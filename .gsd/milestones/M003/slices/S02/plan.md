# S02: Put Screener CLI + Strategy Integration

**Goal:** Wire `screen_puts()` into a standalone CLI and replace `sell_puts()` in `run-strategy`.
**Demo:** User runs `run-put-screener AAPL MSFT GOOG --buying-power 50000` and sees a Rich table. Running `run-strategy` uses `screen_puts()` for the put-selling leg.

## Must-Haves

- `run-put-screener` CLI with Typer: accepts symbols (positional args), `--buying-power` (required), `--preset`, `--config`
- Registered as `run-put-screener` console script in `pyproject.toml`
- `run-strategy` replaces `sell_puts(client, allowed_symbols, buying_power, strat_logger)` with `screen_puts()` + order loop
- `sell_puts` import removed from `scripts/run_strategy.py`
- Strategy integration: iterates `PutRecommendation` list, calls `client.market_sell()` for each, deducts `100 * strike` from buying power, stops when buying power exhausted
- Strategy logger receives put recommendation details
- `sell_calls` import removed from `scripts/run_strategy.py` (already dead per D038)

## Verification

- `python -m pytest tests/test_put_screener.py tests/test_cli_strategy.py -v` — all tests pass
- `python -m pytest tests/ -q` — all 368+ tests pass
- `run-put-screener --help` shows expected flags

## Observability / Diagnostics

- Runtime signals: `run-strategy` logs each put sold with contract details (symbol, strike, DTE, premium, annualized return)
- Failure visibility: logs warning when no put recommendations found, logs buying power exhaustion

## Tasks

- [x] **T01: Build run-put-screener CLI entry point** `est:45m`
  - Why: Standalone CLI for exploring put opportunities — mirrors `run-call-screener` pattern
  - Files: `scripts/run_put_screener.py` (new), `pyproject.toml`, `tests/test_put_screener.py`
  - Do: Create Typer app with `symbols` (variadic positional args), `--buying-power` (required float), `--preset` (optional enum), `--config` (optional path). Load config using same `load_config`/`load_preset`/`deep_merge` pattern as call screener CLI. Call `screen_puts()` and `render_put_results_table()`. Register `run-put-screener` in `pyproject.toml` `[project.scripts]`. Write CLI tests: help text, flag parsing, symbol uppercasing.
  - Verify: `run-put-screener --help` shows flags; `python -m pytest tests/test_put_screener.py -v`
  - Done when: `run-put-screener --help` works and CLI tests pass

- [x] **T02: Wire screen_puts() into run-strategy and remove sell_puts/sell_calls imports** `est:45m`
  - Why: Replaces the last legacy code path with the modern screener
  - Files: `scripts/run_strategy.py`, `tests/test_cli_strategy.py`
  - Do: Remove `from core.execution import sell_puts, sell_calls`. Import `screen_puts` from `screener.put_screener`. Replace `sell_puts(client, allowed_symbols, buying_power, strat_logger)` with: load screener config, call `screen_puts(client.trade_client, client.option_client, allowed_symbols, buying_power, config=cfg)`, iterate recommendations calling `client.market_sell(rec.symbol)` and deducting `100 * rec.strike` from buying_power until exhausted. Log each put sold with details. Update strategy logger calls. Write/update tests: strategy invokes `screen_puts`, no recommendations does not crash, buying power exhaustion stops iteration.
  - Verify: `python -m pytest tests/test_cli_strategy.py tests/ -q`
  - Done when: `run-strategy` no longer imports from `core.execution` and strategy tests confirm `screen_puts()` is called

## Files Likely Touched

- `scripts/run_put_screener.py` (new)
- `scripts/run_strategy.py` (modified)
- `pyproject.toml` (modified)
- `tests/test_put_screener.py` (extended)
- `tests/test_cli_strategy.py` (modified)
