# Codebase Structure

**Analysis Date:** 2026-03-06

## Directory Layout

```
wheeely/
├── config/                  # Configuration: credentials, strategy params, symbol list
│   ├── __init__.py
│   ├── credentials.py       # Loads API keys from .env
│   ├── params.py            # Strategy tuning constants
│   └── symbol_list.txt      # Tradeable ticker symbols (one per line)
├── core/                    # Core business logic
│   ├── __init__.py
│   ├── broker_client.py     # Alpaca API facade (BrokerClient class)
│   ├── cli_args.py          # argparse CLI argument definitions
│   ├── execution.py         # Trade execution orchestration (sell_puts, sell_calls)
│   ├── state_manager.py     # Position state mapping and risk calculation
│   ├── strategy.py          # Pure option filtering, scoring, selection logic
│   ├── user_agent_mixin.py  # Mixin to set custom User-Agent on Alpaca clients
│   └── utils.py             # OCC symbol parsing, timestamp helpers
├── strategy_logging/        # Runtime + JSON strategy logs (does not shadow stdlib)
│   ├── __init__.py
│   ├── logger_setup.py      # Python stdlib logger configuration
│   └── strategy_logger.py   # JSON strategy decision logger (StrategyLogger)
├── models/                  # Data models
│   ├── __init__.py
│   └── contract.py          # Contract dataclass (normalized option representation)
├── reports/                 # Static reports / documentation artifacts
│   └── options-wheel-strategy-test.pdf
├── scripts/                 # Entry point scripts
│   └── run_strategy.py      # main() -- registered as `run-strategy` console script
├── .env                     # API keys (git-ignored, required at runtime)
├── .gitignore
├── CLAUDE.md                # Claude Code project guidance
├── LICENSE                  # MIT License
├── README.md                # Project documentation
└── pyproject.toml           # Build config, dependencies, console script registration
```

## Directory Purposes

**`config/`:**
- Purpose: All configuration -- credentials, strategy parameters, and the symbol watchlist
- Contains: Python modules exporting constants; one plain-text file (`symbol_list.txt`)
- Key files: `params.py` (all tuning knobs), `credentials.py` (env var loading), `symbol_list.txt` (ticker list)

**`core/`:**
- Purpose: All business logic for the options wheel strategy
- Contains: Broker API wrapper, strategy algorithms, execution orchestration, state management, CLI parsing, utilities
- Key files: `broker_client.py` (API facade), `execution.py` (trade pipelines), `strategy.py` (filtering/scoring), `state_manager.py` (wheel state)

**`strategy_logging/`:**
- Purpose: Logging configuration and structured strategy logging
- Contains: Two separate logging systems
- Key files: `logger_setup.py` (stdlib logger), `strategy_logger.py` (JSON audit logger)
- Named to avoid shadowing Python's stdlib `logging` package.

**`models/`:**
- Purpose: Data model definitions for normalizing external API objects
- Contains: Single dataclass definition
- Key files: `contract.py` (the `Contract` dataclass)

**`scripts/`:**
- Purpose: CLI entry points
- Contains: Main runner script
- Key files: `run_strategy.py` (the only entry point)

**`reports/`:**
- Purpose: Static report artifacts
- Contains: PDF documentation
- Key files: `options-wheel-strategy-test.pdf`

## Key File Locations

**Entry Points:**
- `scripts/run_strategy.py`: Sole entry point, registered as `run-strategy` in `pyproject.toml`

**Configuration:**
- `pyproject.toml`: Build system, dependencies, console script registration
- `config/params.py`: All strategy tuning constants (delta range, yield range, DTE range, risk limits, scoring thresholds)
- `config/credentials.py`: Loads `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `IS_PAPER` from `.env`
- `config/symbol_list.txt`: Newline-delimited list of ticker symbols to trade

**Core Logic:**
- `core/broker_client.py`: `BrokerClient` class -- all Alpaca API interaction
- `core/strategy.py`: `filter_underlying()`, `filter_options()`, `score_options()`, `select_options()` -- pure strategy functions
- `core/execution.py`: `sell_puts()`, `sell_calls()` -- trade execution pipelines
- `core/state_manager.py`: `update_state()`, `calculate_risk()` -- position analysis

**Models:**
- `models/contract.py`: `Contract` dataclass with constructors `from_contract()`, `from_contract_snapshot()`, `from_dict()`

**Logging:**
- `strategy_logging/logger_setup.py`: `setup_logger()` -- configures Python stdlib logger
- `strategy_logging/strategy_logger.py`: `StrategyLogger` class -- JSON audit trail

**Utilities:**
- `core/utils.py`: `parse_option_symbol()`, `get_ny_timestamp()`
- `core/user_agent_mixin.py`: `UserAgentMixin` class
- `core/cli_args.py`: `parse_args()` -- argparse definitions

## Naming Conventions

**Files:**
- `snake_case.py` for all Python modules: `broker_client.py`, `state_manager.py`, `strategy_logger.py`
- Plain text config: `symbol_list.txt`
- Top-level metadata: `UPPERCASE.md` (README, LICENSE, CLAUDE)

**Directories:**
- `snake_case` for all packages: `core/`, `config/`, `strategy_logging/`, `models/`, `scripts/`, `reports/`

**Classes:**
- `PascalCase`: `BrokerClient`, `Contract`, `StrategyLogger`, `UserAgentMixin`
- SDK subclasses use descriptive suffixes: `TradingClientSigned`, `StockHistoricalDataClientSigned`

**Functions:**
- `snake_case`: `sell_puts()`, `filter_options()`, `score_options()`, `parse_option_symbol()`

**Constants:**
- `UPPER_SNAKE_CASE`: `MAX_RISK`, `DELTA_MIN`, `EXPIRATION_MAX`, `SCORE_MIN`, `USER_AGENT`

## Where to Add New Code

**New Strategy Logic (filtering, scoring, selection):**
- Add pure functions to `core/strategy.py`
- Wire into pipeline in `core/execution.py`
- Add any new tuning constants to `config/params.py`

**New Broker API Methods:**
- Add methods to `BrokerClient` in `core/broker_client.py`
- Follow existing patterns: wrap Alpaca SDK request objects, handle pagination/batching internally

**New Data Models:**
- Add new dataclass files to `models/` (e.g., `models/position.py`)
- Follow `Contract` pattern: use `@dataclass`, provide `from_*` classmethods and `to_dict()`

**New CLI Flags:**
- Add `parser.add_argument()` calls in `core/cli_args.py`
- Handle in `scripts/run_strategy.py:main()`

**New Utility Functions:**
- General utilities: `core/utils.py`
- Logging-related: `strategy_logging/` package

**New Tradeable Symbols:**
- Append ticker to `config/symbol_list.txt` (one per line)

**New Entry Point Scripts:**
- Add to `scripts/` directory
- Register in `pyproject.toml` under `[project.scripts]`

**Tests (when added):**
- Create a `tests/` directory at project root
- Mirror `core/`, `models/`, `config/` structure inside `tests/`

## Special Directories

**`logs/` (git-ignored):**
- Purpose: Runtime log output
- Contains: `run.log` (Python logger file output), `strategy_log.json` (StrategyLogger JSON audit)
- Generated: Yes, at runtime when `--log-to-file` or `--strat-log` flags are used
- Committed: No (in `.gitignore`)

**`archive/` (git-ignored):**
- Purpose: Archived/old code or data
- Generated: Manual
- Committed: No (in `.gitignore`, excluded from setuptools package discovery)

**`figures/` (git-ignored):**
- Purpose: Generated charts/visualizations
- Generated: Yes (likely from analysis notebooks)
- Committed: No (in `.gitignore`)

**`reports/`:**
- Purpose: Static documentation artifacts (PDFs, etc.)
- Generated: No (manually added)
- Committed: Yes

---

*Structure analysis: 2026-03-06*
