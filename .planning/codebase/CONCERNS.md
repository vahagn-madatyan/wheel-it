# Codebase Concerns

**Analysis Date:** 2026-03-06

## Tech Debt

**Zero Test Coverage:**
- Issue: The project has no tests whatsoever. CLAUDE.md explicitly states "There are no tests in this project currently."
- Files: All files under `core/`, `models/`, `config/`, `logging/`, `scripts/`
- Impact: Every change risks breaking the strategy logic, state management, or order execution with no safety net. This is a financial trading system where bugs can cause real monetary loss.
- Fix approach: Add unit tests for pure functions in `core/strategy.py` (filter, score, select). Add integration tests for `core/state_manager.py` with mock positions. Mock `BrokerClient` for `core/execution.py` tests.

**stdlib `logging` Module Shadowing:**
- Issue: ~~The project has a `logging/` package that shadows Python's built-in `logging` module.~~ **Fixed.** The package is now `strategy_logging/`, so `import logging` is stdlib.
- Files: `strategy_logging/__init__.py`, `strategy_logging/logger_setup.py`, `strategy_logging/strategy_logger.py`
- Impact: A pip/pipx install previously failed with `ModuleNotFoundError: logging.logger_setup` because stdlib always precedes `site-packages` on `sys.path`.
- Fix approach: Rename applied (`logging/` → `strategy_logging/`). The stdlib-reexport shim in `__init__.py` was deleted.

**Unpinned Dependencies:**
- Issue: `pyproject.toml` specifies loose version constraints (`pandas>=1.5`, `numpy>=1.23`, `alpaca-py` with no version). No lockfile exists.
- Files: `pyproject.toml`
- Impact: Builds are not reproducible. A new `alpaca-py` release could introduce breaking API changes. `numpy>=1.23` spans major version boundaries (numpy 1.x vs 2.x have breaking changes).
- Fix approach: Pin `alpaca-py` to a specific version range. Add a `uv.lock` or `requirements.lock` file. Consider upper-bound constraints for major versions.

**Placeholder Author in pyproject.toml:**
- Issue: Author is set to `"Your Name"` with email `"your.email@example.com"`.
- Files: `pyproject.toml` (line 10)
- Impact: Minor, but indicates incomplete project setup.
- Fix approach: Update to actual author information.

**Commented-Out Code in Contract.update():**
- Issue: Lines 90-94 in `models/contract.py` contain commented-out code for fetching underlying stock price.
- Files: `models/contract.py` (lines 90-94)
- Impact: Dead code clutter; unclear whether this is planned functionality or abandoned.
- Fix approach: Remove or implement behind a flag.

**Mixed Timezone Libraries:**
- Issue: `core/utils.py` uses `pytz` for timezone handling while `core/broker_client.py` uses `zoneinfo.ZoneInfo`. These are two different timezone libraries doing the same thing.
- Files: `core/utils.py` (line 2), `core/broker_client.py` (line 10)
- Impact: Inconsistency; `pytz` is a legacy library and `zoneinfo` (stdlib since Python 3.9) is the modern replacement. Having both creates confusion.
- Fix approach: Standardize on `zoneinfo.ZoneInfo` throughout. Remove `pytz` dependency (note: `pytz` is not even declared in `pyproject.toml` dependencies, so it is an undeclared transitive dependency).

**`pytz` Is an Undeclared Dependency:**
- Issue: `core/utils.py` imports `pytz` but it is not listed in `pyproject.toml` dependencies.
- Files: `core/utils.py`, `pyproject.toml`
- Impact: Fresh installs may fail if `pytz` is not pulled in transitively. Currently works only because `alpaca-py` or `pandas` likely pulls it in.
- Fix approach: Either add `pytz` to dependencies or replace with `zoneinfo` (preferred).

## Known Bugs

**`strat_logger` Called Unconditionally on Line 17 of execution.py:**
- Symptoms: `sell_puts()` calls `strat_logger.set_filtered_symbols()` on line 17 without checking if `strat_logger` is `None`, but the parameter defaults to `None`. Other calls on lines 24-25 and 37-38 correctly check `if strat_logger:` first.
- Files: `core/execution.py` (line 17)
- Trigger: Call `sell_puts()` without passing a `strat_logger` argument.
- Workaround: Always pass a `strat_logger` (current usage in `scripts/run_strategy.py` always does, but the function signature allows `None`).

**`sell_calls` Logs Inconsistently:**
- Symptoms: `strat_logger.log_sold_puts()` is called with a list (`[p.to_dict()]`) in `sell_puts()` line 38, but `strat_logger.log_sold_calls()` is called with a plain dict (`contract.to_dict()`) in `sell_calls()` line 62. The `log_sold_puts` and `log_sold_calls` methods both append their argument to a list, so `log_sold_puts` appends a list-within-a-list.
- Files: `core/execution.py` (lines 38, 62), `logging/strategy_logger.py` (lines 60-70)
- Trigger: Run the strategy with `--strat-log`. The JSON output will have inconsistent nesting for sold puts vs sold calls.
- Workaround: None currently.

**`Contract.from_contract` Uses `datetime.date.today()` Instead of NY Timezone:**
- Symptoms: DTE calculation uses local system date which may differ from NYSE trading date (e.g., after market close on the West Coast, or on a server in UTC).
- Files: `models/contract.py` (line 40, 58)
- Trigger: Run the bot from a non-Eastern-timezone machine near midnight.
- Workaround: Ensure the bot runs during Eastern business hours.

## Security Considerations

**Credentials Loaded at Module Import Time:**
- Risk: `config/credentials.py` loads API keys from `.env` at import time using `load_dotenv(override=True)`. The `override=True` means `.env` values override actual environment variables, which could mask production secrets set via environment.
- Files: `config/credentials.py`
- Current mitigation: `.env` is in `.gitignore`.
- Recommendations: Remove `override=True` to let real environment variables take precedence. Consider validating that keys are present at startup and failing fast with a clear error.

**No Validation of API Keys at Startup:**
- Risk: If `.env` is missing or keys are empty, the bot will proceed and fail with cryptic Alpaca SDK errors.
- Files: `config/credentials.py`, `scripts/run_strategy.py`
- Current mitigation: None.
- Recommendations: Add explicit checks that `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` are non-empty strings before constructing `BrokerClient`.

**Market Orders Only:**
- Risk: All option orders use market orders (`client.market_sell()` with no price limit). In illiquid option markets, this risks adverse fills at prices far from the expected bid.
- Files: `core/broker_client.py` (lines 32-36), `core/execution.py` (lines 36, 60)
- Current mitigation: The `OPEN_INTEREST_MIN = 100` filter provides some liquidity screening.
- Recommendations: Consider limit orders at the bid price, or at minimum a price floor/ceiling check before submitting.

**No Paper/Live Safety Guard:**
- Risk: The `IS_PAPER` flag defaults to `true`, but there is no confirmation prompt or safeguard when switching to live trading. A misconfigured `.env` could trade real money.
- Files: `config/credentials.py` (line 8), `scripts/run_strategy.py`
- Current mitigation: Default is paper mode.
- Recommendations: Add a confirmation prompt or explicit `--live` flag requirement when `IS_PAPER=false`.

## Performance Bottlenecks

**Individual API Calls per Contract in `sell_calls`:**
- Problem: `sell_calls()` in `core/execution.py` line 52 calls `Contract.from_contract(option, client)` for every contract, which triggers `__post_init__` -> `update()` -> individual API snapshot call per contract. This is N+1 API calls instead of batching.
- Files: `core/execution.py` (line 52), `models/contract.py` (lines 26-28, 70-88)
- Cause: `sell_calls` uses the `from_contract` constructor (which fetches snapshots one at a time) instead of the `from_contract_snapshot` pattern used by `sell_puts` (which batch-fetches snapshots).
- Improvement path: Refactor `sell_calls` to follow the same batch pattern as `sell_puts`: fetch all contracts, batch-fetch snapshots, then create `Contract` objects via `from_contract_snapshot`.

**No Rate Limiting on API Calls:**
- Problem: No explicit rate limiting or backoff on Alpaca API calls. With many symbols and large contract lists, the bot could hit API rate limits.
- Files: `core/broker_client.py`
- Cause: Missing retry/backoff logic.
- Improvement path: Add exponential backoff or use Alpaca SDK's built-in rate limiting if available.

## Fragile Areas

**State Manager Position Parsing:**
- Files: `core/state_manager.py`
- Why fragile: `update_state()` assumes strict wheel state transitions and raises `ValueError` on any unexpected combination. If Alpaca returns positions in an unexpected order or with edge-case states (e.g., partial fills, manual trades outside the bot), the entire run crashes.
- Safe modification: Add a recovery/skip mode that logs unexpected states instead of crashing. Consider a `--strict` flag for the current behavior.
- Test coverage: Zero tests.

**Option Symbol Parsing Regex:**
- Files: `core/utils.py` (line 12)
- Why fragile: The regex `r'^([A-Za-z]+)(\d{6})([PC])(\d{8})$'` works for standard OCC symbols but will fail for symbols with special characters (e.g., `BRK/B`, `BF.B`) or non-standard formats.
- Safe modification: Test against a comprehensive set of OCC symbols including edge cases before changing.
- Test coverage: Zero tests.

**`logging/` Package Import Order:**
- Files: `logging/__init__.py`, `logging/logger_setup.py`
- Why fragile: The stdlib shadowing means import order matters. If any module does `import logging` before the custom package is set up, behavior is unpredictable. The `logging/__init__.py` is empty, so `logging/logger_setup.py` imports stdlib `logging` successfully only because Python resolves `import logging` to stdlib when called from within the `logging/` package (due to how relative imports work in `__init__.py`). This is subtle and easy to break.
- Safe modification: Rename the package (see Tech Debt section above).
- Test coverage: Zero tests.

**`fresh-start` Mode Liquidates Everything:**
- Files: `core/broker_client.py` (lines 96-105), `scripts/run_strategy.py` (lines 26-30)
- Why fragile: `liquidate_all_positions()` closes ALL positions (options first, then equities) without confirmation. If the user has positions from other strategies or manual trades in the same Alpaca account, they will all be liquidated.
- Safe modification: Filter to only liquidate positions in symbols from `symbol_list.txt`. Add a confirmation step.
- Test coverage: Zero tests.

## Scaling Limits

**Single-Threaded Execution:**
- Current capacity: Processes one symbol at a time sequentially.
- Limit: As the symbol list grows, the strategy run time increases linearly due to sequential API calls (especially the N+1 calls in `sell_calls`).
- Scaling path: Batch API calls, parallelize per-symbol processing with `asyncio` or `concurrent.futures`.

**Single JSON Log File:**
- Current capacity: `logs/strategy_log.json` is a single file that grows with every run (appended as a JSON array).
- Limit: After thousands of runs, the file will become large and slow to read/write (entire file is read and rewritten on each save).
- Scaling path: Use date-based log rotation or a database for strategy logs.

## Dependencies at Risk

**`alpaca-py` Unpinned:**
- Risk: No version constraint means any breaking change in `alpaca-py` could break the bot silently.
- Impact: All API interactions go through `BrokerClient` which wraps `alpaca-py` classes. A change in response structure, pagination, or authentication could break everything.
- Migration plan: Pin to a specific minor version range (e.g., `alpaca-py>=0.20,<0.21`). Add integration tests against the SDK.

**`numpy` Used Minimally:**
- Risk: `numpy` is a heavy dependency used only for `np.argmax()` in `core/execution.py` line 58.
- Impact: Adds significant install size for a single function call.
- Migration plan: Replace `np.argmax(scores)` with `scores.index(max(scores))` (pure Python) and remove `numpy` from dependencies.

## Missing Critical Features

**No Order Confirmation or Validation:**
- Problem: Orders are placed with no pre-trade validation (e.g., verifying the account has sufficient buying power via API, checking market hours, verifying the option is still active).
- Blocks: Safe production use of the bot.

**No Error Recovery or Retry:**
- Problem: If an API call fails mid-execution (e.g., network issue after selling some puts but before selling others), there is no recovery mechanism. The bot simply crashes and leaves partial state.
- Blocks: Reliable unattended operation.

**No Scheduling/Automation:**
- Problem: The bot runs once per invocation. There is no cron, scheduler, or daemon mode for repeated execution during trading hours.
- Blocks: Truly automated wheel strategy execution.

**No Position Tracking Across Runs:**
- Problem: The bot relies entirely on Alpaca's position API to determine wheel state. It has no local persistence of what it sold, at what price, or why. The JSON strategy log is append-only and not consumed by the bot itself.
- Blocks: Performance tracking, P&L analysis, and strategy refinement.

## Test Coverage Gaps

**All Code Is Untested:**
- What's not tested: Every module -- strategy filtering/scoring, state management, order execution, option symbol parsing, contract creation, logging.
- Files: `core/strategy.py`, `core/state_manager.py`, `core/execution.py`, `core/utils.py`, `core/broker_client.py`, `models/contract.py`, `logging/strategy_logger.py`
- Risk: Financial trading logic has zero automated verification. A typo in the scoring formula or filter logic could cause the bot to sell options at terrible prices or violate risk limits.
- Priority: **High** -- `core/strategy.py` and `core/state_manager.py` are pure logic with no API dependencies and are straightforward to test. Start there.

---

*Concerns audit: 2026-03-06*
