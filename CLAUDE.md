# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated options wheel strategy bot using the Alpaca Trading API. Sells cash-secured puts on selected stocks, handles assignments, then sells covered calls — repeating the cycle to collect premiums.

## Setup & Commands

```bash
uv venv && source .venv/bin/activate
uv pip install -e .
```

Requires a `.env` file with `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, and `IS_PAPER=true|false`.

**Run the strategy:**
```bash
run-strategy                    # normal run
run-strategy --fresh-start      # liquidate all positions first
run-strategy --strat-log        # enable JSON strategy logging
run-strategy --log-level DEBUG --log-to-file
run-strategy --screen           # run screener before strategy
```

**Screener CLIs:**
```bash
run-screener --preset moderate              # screen stocks for put selling
run-screener --preset moderate --top-n 20   # cap to top 20 worst performers
run-put-screener AAPL MSFT GOOG --buying-power 50000    # explore put opportunities
run-put-screener AAPL --buying-power 20000 --preset conservative
run-call-screener AAPL --cost-basis 175     # explore covered call opportunities
```

**Run tests:**
```bash
python -m pytest tests/ -q          # full test suite (~425 tests, <1s)
python -m pytest tests/ -v          # verbose output
```

## Architecture

**Entry point:** `scripts/run_strategy.py:main()` — registered as `run-strategy` console script in `pyproject.toml`.

**Flow:** `main()` → check positions via `state_manager.update_state()` → sell covered calls on assigned stock via `screen_calls()` → sell new puts on remaining symbols via `screen_puts()` within buying power.

### Key Modules

- **`core/broker_client.py`** — `BrokerClient` wraps three Alpaca SDK clients (trading, stock data, option data) with `UserAgentMixin`. Provides `get_positions()`, `market_sell()`, and `liquidate_all_positions()`.
- **`core/state_manager.py`** — `update_state()` maps current positions to wheel states: `short_put`, `long_shares`, or `short_call`. `calculate_risk()` computes capital at risk.
- **`screener/put_screener.py`** — `PutRecommendation` dataclass, `screen_puts()` for multi-symbol put screening with buying power pre-filter, OI/spread/delta filters, one-per-underlying diversification, and annualized return ranking. `render_put_results_table()` for Rich display.
- **`screener/call_screener.py`** — `CallRecommendation` dataclass, `screen_calls()` for single-symbol covered call screening with strike ≥ cost basis enforcement. `render_call_results_table()` for Rich display.
- **`screener/pipeline.py`** — Stock screening pipeline: 4-stage funnel (Stage 1: Alpaca technicals + HV → Stage 1b: Finnhub earnings → Stage 2: Finnhub fundamentals → Stage 3: options chain validation). 10+ filter functions returning `FilterResult`, scoring engine, pipeline orchestrator.
- **`screener/config_loader.py`** — YAML config loading with Pydantic validation, preset resolution (conservative/moderate/aggressive).
- **`screener/finnhub_client.py`** — Rate-limited Finnhub API client with earnings calendar.
- **`screener/market_data.py`** — Alpaca bar fetching, technical indicator computation, monthly performance.
- **`screener/display.py`** — Rich table display for screener results, filter summaries, progress indicators.
- **`config/params.py`** — Strategy tuning constants: `MAX_RISK` (max dollar risk), `DELTA_MIN`/`DELTA_MAX` (delta range for option selection).
- **`config/symbol_list.txt`** — One ticker per line. Only these symbols are traded.
- **`logging/strategy_logger.py`** — JSON logger for strategy decisions (separate from Python's `logging`). Note: the `logging/` package shadows Python's stdlib `logging` — imports use `from logging.logger_setup import ...` for the custom module.

### Important Patterns

- The project shadows Python's `logging` module with its own `logging/` package. The custom `logger_setup.py` internally imports `logging` (stdlib) via the package's `__init__.py`.
- Both screeners (`screen_puts()` and `screen_calls()`) use Alpaca SDK clients directly (not `BrokerClient` wrapper methods) for contract fetching and snapshot batching.
- `screen_puts()` paginates multi-symbol contract fetches (1000 per page) and batches snapshot requests (100 per batch).
- Options are filtered to one contract per underlying symbol to promote diversification.
- Risk is tracked as `strike * 100` per short put and `entry_price * qty` per stock position.
- None-delta contracts pass the delta filter (D039) — absence of greeks data shouldn't eliminate tradeable contracts.
- Put annualized return uses `premium/strike` (D046), call uses `premium/cost_basis`.
