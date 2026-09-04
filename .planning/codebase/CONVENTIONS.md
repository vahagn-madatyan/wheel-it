# Coding Conventions

**Analysis Date:** 2026-03-06

## Naming Patterns

**Files:**
- Use `snake_case.py` for all Python modules: `broker_client.py`, `state_manager.py`, `cli_args.py`
- Configuration text files use `snake_case.txt`: `symbol_list.txt`
- `__init__.py` files are present but empty in all packages

**Functions:**
- Use `snake_case` for all functions: `sell_puts()`, `filter_underlying()`, `parse_option_symbol()`
- Prefix with verb describing the action: `get_`, `sell_`, `filter_`, `score_`, `select_`, `parse_`, `calculate_`, `update_`, `setup_`
- Setters in `StrategyLogger` use `set_` prefix: `set_buying_power()`, `set_allowed_symbols()`
- Logging methods in `StrategyLogger` use `log_` prefix: `log_put_options()`, `log_sold_calls()`
- Add-style methods use `add_` prefix: `add_current_positions()`, `add_state_dict()`

**Variables:**
- Use `snake_case` for local variables and parameters: `buying_power`, `option_contracts`, `filtered_symbols`
- Use `UPPER_SNAKE_CASE` for module-level constants: `MAX_RISK`, `DELTA_MIN`, `EXPIRATION_MAX`, `USER_AGENT`
- Use `UPPER_SNAKE_CASE` for script-level constants inside `main()`: `SYMBOLS_FILE`, `SYMBOLS`

**Classes:**
- Use `PascalCase`: `BrokerClient`, `Contract`, `StrategyLogger`, `UserAgentMixin`
- Alpaca SDK subclasses append `Signed` suffix: `TradingClientSigned`, `StockHistoricalDataClientSigned`

**Parameters:**
- Use `snake_case`: `buying_power_limit`, `contract_type`, `min_strike`
- Optional parameters use default values directly (not `Optional` in signature): `def market_sell(self, symbol, qty=1)`

## Code Style

**Formatting:**
- No formatter configured (no `.prettierrc`, `.editorconfig`, or similar)
- Indentation: 4 spaces (standard Python)
- Line length: no enforced limit; some lines exceed 120 characters (see list comprehensions in `core/strategy.py` and `core/execution.py`)
- Trailing whitespace present in some files

**Linting:**
- No linter configured (no `.flake8`, `pylintrc`, `ruff.toml`, or similar)
- No `[tool.ruff]` or `[tool.pylint]` section in `pyproject.toml`

**Type Hints:**
- Used sparingly and inconsistently
- `models/contract.py` uses `Optional[float]`, `Optional[int]`, return type `-> "Contract"` on classmethods
- `logging/strategy_logger.py` uses type hints on some parameters: `is_fresh_start: bool`, `symbols: list`, `call_options: list[dict]`
- Most functions in `core/` have no type hints at all
- When adding new code, follow the existing pattern: use type hints on dataclass fields and classmethod return types; function parameters and returns are optional

## Import Organization

**Order:**
1. Standard library imports (`import re`, `import datetime`, `from pathlib import Path`)
2. Third-party imports (`from alpaca.trading.client import TradingClient`, `import numpy as np`)
3. Local project imports (`from config.params import ...`, `from core.broker_client import ...`, `from .strategy import ...`)

**Style:**
- Use `from X import Y` for specific items; avoid bare `import X` except for `datetime`, `json`, `re`, `logging`, `sys`
- Relative imports within the same package: `from .strategy import ...`, `from .utils import ...` (see `core/execution.py`, `core/state_manager.py`)
- Absolute imports across packages: `from config.params import ...`, `from models.contract import Contract`
- No `__all__` exports defined in any module

**Path Aliases:**
- None. All imports use direct package paths from project root.

## Error Handling

**Patterns:**
- Raise `ValueError` for all domain errors with descriptive f-string messages
- Examples in `core/state_manager.py`:
  ```python
  raise ValueError(f"Only long stock positions allowed! Got {p.symbol} with qty {p.qty}")
  raise ValueError(f"Unexpected state for {underlying}: {state[underlying]}")
  raise ValueError(f"Invalid final state for {underlying}: {st}")
  ```
- `core/broker_client.py` raises `ValueError` for invalid input types:
  ```python
  raise ValueError("Input must be a string or list of strings representing symbols.")
  ```
- `models/contract.py` raises `ValueError` when required data is missing:
  ```python
  raise ValueError(f"Snapshot data is required to create a Contract from a snapshot for symbol {contract.symbol}.")
  ```
- No try/except blocks anywhere in the codebase. Errors propagate to the top-level `main()` and crash the process.
- No custom exception classes. All exceptions are `ValueError`.
- Guard clauses with early return used in `core/execution.py`:
  ```python
  if not allowed_symbols or buying_power <= 0:
      return
  ```

## Logging

**Framework:** Python stdlib `logging` module

Logging helpers live in `strategy_logging/` so they do not shadow Python's stdlib `logging`. External modules use `from strategy_logging.logger_setup import setup_logger`.

**Logger hierarchy:**
- Root strategy logger: `logging.getLogger("strategy")` (configured in `strategy_logging/logger_setup.py`)
- Child loggers per module: `logging.getLogger(f"strategy.{__name__}")` (see `core/execution.py`)

**Patterns:**
- Use `logger.info()` for normal operational messages: "Searching for put options...", "Selling put: {symbol}"
- Use `logger.error()` before raising exceptions (see `core/execution.py` line 48-49)
- Use f-strings for log message formatting (not lazy `%` formatting)
- Console format: `[%(message)s]` (bracketed, message only)
- File format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

**Strategy Logger (separate system):**
- `strategy_logging/strategy_logger.py` provides `StrategyLogger` class for structured JSON logging of strategy decisions
- Writes to `logs/strategy_log.json` as an appended JSON array
- All methods check `self.enabled` before writing (no-op when disabled)

## Comments

**When to Comment:**
- Module-level constants get inline comments explaining their purpose (see `config/params.py`)
- Complex logic gets a brief inline explanation
- No excessive commenting; most code is self-documenting through function/variable names

**Docstrings:**
- Present on key public functions using triple-double-quote style
- Format: single paragraph, no parameter documentation
- Examples from `core/strategy.py`:
  ```python
  def filter_underlying(client, symbols, buying_power_limit):
      """
      Filter underlying symbols based on buying power.  Can add custom logic such as volatility or ranging / support metrics.
      """
  ```
- Not every function has a docstring; utility functions and simple methods may omit them

## Function Design

**Size:** Functions are small, typically 5-30 lines. The largest function is `update_state()` at ~40 lines.

**Parameters:**
- Positional parameters for required args
- Keyword arguments with defaults for optional args: `def filter_options(options, min_strike=0)`
- `client` (BrokerClient) is passed as first parameter to functions needing API access
- `strat_logger` is passed as last parameter with `None` default to functions that optionally log

**Return Values:**
- Functions return lists, dicts, or None (implicit)
- `filter_*` functions return filtered lists
- `score_options` returns a parallel list of scores (same index as input)
- `select_options` returns a list of Contract objects
- `update_state` returns a dict mapping symbol to state dict

## Module Design

**Exports:**
- No `__all__` defined anywhere
- All `__init__.py` files are empty
- Consumers import specific names directly from module files

**Separation of Concerns:**
- `core/strategy.py` contains pure functions (no API calls, no side effects)
- `core/execution.py` orchestrates API calls + strategy logic
- `core/broker_client.py` wraps all external API interaction
- `core/state_manager.py` handles position state mapping
- `models/contract.py` is a data normalization layer (dataclass)
- `config/params.py` holds tuning constants only

**Dataclasses:**
- `models/contract.py` uses `@dataclass` with `Optional` fields defaulting to `None`
- Multiple `@classmethod` constructors: `from_contract()`, `from_contract_snapshot()`, `from_dict()`
- Serialization via `to_dict()` method and `save_to_json()` / `load_from_json()` static methods

---

*Convention analysis: 2026-03-06*
