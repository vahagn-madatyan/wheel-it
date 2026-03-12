# Phase 5: CLI and Integration - Research

**Researched:** 2026-03-10
**Domain:** CLI framework (Typer), argparse migration, symbol list export with position safety
**Confidence:** HIGH

## Summary

Phase 5 wires the screener pipeline (built in Phases 1-4) into two CLI entry points using Typer: a standalone `run-screener` command and a `--screen` flag on the existing `run-strategy` command. The core challenge is migrating `run-strategy` from argparse to Typer while preserving all existing behavior, then building `run-screener` with display, preset override, config path, verbose, and `--update-symbols` flags. The `--update-symbols` path requires active position detection via `BrokerClient.get_positions()` + `state_manager.update_state()` to protect symbols with open wheel positions from removal.

Typer 0.24.1 is the standard choice and already depends on Rich (which is in the project). The project uses Python 3.14, well above Typer's >=3.10 requirement. The main integration risk is the project's `logging/` package shadow -- Typer modules must use `import logging as stdlib_logging` consistently. The argparse-to-Typer migration is straightforward since the existing CLI is simple (4 flags, no subcommands).

**Primary recommendation:** Use Typer 0.24.1 with `Annotated` syntax for all CLI definitions. Create a shared `cli_common.py` module for credential loading and logger setup used by both entry points. Keep `run-screener` and `run-strategy` as separate Typer apps (not subcommands of a parent app) since they serve different user workflows.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Two entry points**: standalone `run-screener` command AND `run-strategy --screen` flag, both calling the same screener pipeline
- **Typer framework** for both commands -- migrate existing `run-strategy` from argparse to Typer for consistency
- New entry point: `scripts/run_screener.py` (mirrors existing `scripts/run_strategy.py` pattern)
- `pyproject.toml` gets a second `[project.scripts]` entry: `run-screener = "scripts.run_screener:main"`
- Existing `core/cli_args.py` (argparse) replaced with Typer-based CLI definitions
- `--update-symbols` flag triggers writing screened symbols to `config/symbol_list.txt`
- **Active position detection** via Alpaca positions API (`BrokerClient.get_positions()`) -- same API already used by run-strategy
- Protected symbols (short puts, assigned shares, short calls) **kept in list + warning printed**: "AAPL: kept (active short put)"
- **Diff shown before writing**: "+NVDA, +AMD, -INTC (screened out)" -- no confirmation prompt, just informational
- `--update-symbols` **requires Alpaca credentials** -- hard error if missing: "requires Alpaca credentials for position protection"
- `run-strategy --screen` runs screener first, auto-updates `symbol_list.txt` (with position protection), then proceeds with strategy on the updated list
- Full Rich results table displayed even when running before strategy -- user sees what they're trading
- **Zero results handling**: warn and proceed with existing symbol list -- "Warning: screener found 0 passing stocks. Using existing symbol_list.txt."
- `--screen` and `--fresh-start` can be combined: screen first (update symbols), then fresh-start (liquidate and trade on new list)
- **Default output** (`run-screener` with no flags): Rich results table + stage summary panel (funnel from universe to scored)
- `--output-only` is the default behavior (display results, don't modify files)
- `--verbose` adds: per-filter breakdown waterfall + per-symbol filter decisions (why each eliminated stock was removed)
- `--preset` flag: `run-screener --preset aggressive` overrides config file preset without editing screener.yaml
- `--config` flag: `run-screener --config path/to/custom.yaml` for custom config file path
- Progress bars shown during pipeline execution (already wired via `on_progress` callback from Phase 4)
- Diff output: green for added symbols, red for removed, yellow for protected (active positions)
- Per-symbol filter decisions in --verbose mode should show what filter failed and the actual vs threshold value (FilterResult already has actual_value, threshold, reason fields)
- The --screen flag on run-strategy should feel seamless -- screener output appears, then strategy continues below it

### Claude's Discretion
- Typer app structure (single app vs separate apps for strategy/screener)
- How to share common CLI setup (logging, credentials) between run-strategy and run-screener
- Per-symbol verbose output formatting
- How to structure the Typer migration of run-strategy (minimal changes to existing behavior)

### Deferred Ideas (OUT OF SCOPE)
- v2 OUTP-05: Options chain preview alongside each result (best put strike, premium, delta)
- v2 OUTP-06: --dry-run mode showing what would change in symbol_list.txt
- v2 PERF-02: --verbose per-symbol filter decisions (partial implementation in v1 -- full verbose logging in v2)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLI-01 | User can run screener standalone via `run-screener` CLI command | Typer app in `scripts/run_screener.py`, pyproject.toml entry point, pipeline + display integration |
| CLI-02 | User can run screener before strategy via `run-strategy --screen` flag | Typer migration of run_strategy.py, `--screen` boolean flag, screener pipeline call before strategy logic |
| CLI-03 | Screener CLI accepts --update-symbols flag to write results to symbol_list.txt | Typer boolean flag, symbol export function with position protection, diff display |
| CLI-04 | Screener CLI accepts --output-only flag (default) to display results without updating files | Typer boolean flag defaulting True, controls whether symbol_list.txt is written |
| OUTP-03 | Screener can export filtered symbols to config/symbol_list.txt via --update-symbols flag | Symbol list write function, position-safe merge logic, Rich diff output |
| SAFE-03 | Symbol list export protects actively-traded symbols from removal | `BrokerClient.get_positions()` + `update_state()` for position detection, protected symbol set, merge logic |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| typer | 0.24.1 | CLI framework with type hints | Modern Python CLI standard; built on Click; auto-generates help; depends on Rich (already in project) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rich | >=14.0 | Terminal formatting | Already in project; used by screener display; Typer auto-uses for error formatting |

### Already in Project (no new installs needed beyond typer)
| Library | Purpose | Used By |
|---------|---------|---------|
| rich | Results table, progress bars, colored diff output | screener/display.py |
| pydantic | Config validation | screener/config_loader.py |
| python-dotenv | .env loading | config/credentials.py |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Typer | Click | Typer is built on Click with type-hint-driven API; less boilerplate; user locked this decision |
| Typer | argparse (keep) | argparse works but no Rich integration, no auto-help, more verbose; user locked Typer decision |

**Installation:**
```bash
uv pip install typer
```

Then add to pyproject.toml dependencies:
```toml
dependencies = [
    # ... existing ...
    "typer>=0.9.0",
]
```

**Note on pyproject.toml `requires-python`:** Currently set to `>=3.8`. Typer 0.24.1 requires `>=3.10`. The project actually uses Python 3.14. The `requires-python` field could be updated to `>=3.10` for accuracy, but this is cosmetic since the actual environment exceeds both thresholds.

## Architecture Patterns

### Recommended Project Structure
```
scripts/
  run_strategy.py      # Typer app (migrated from argparse)
  run_screener.py      # New Typer app for standalone screener
core/
  cli_args.py          # DELETE (replaced by Typer definitions in scripts/)
  cli_common.py        # NEW: shared CLI setup (logging, credentials)
  broker_client.py     # Existing (get_positions used for safety)
  state_manager.py     # Existing (update_state used for position detection)
screener/
  pipeline.py          # Existing (run_pipeline called by both entry points)
  display.py           # Existing (render functions called by CLI)
  export.py            # NEW: symbol list export with position protection
config/
  symbol_list.txt      # Write target for --update-symbols
```

### Pattern 1: Separate Typer Apps (Recommended)
**What:** Each entry point (`run-screener`, `run-strategy`) has its own `typer.Typer()` app instance.
**When to use:** When commands have different parameter sets and serve different workflows.
**Why not a single app:** `run-screener` and `run-strategy` have mostly different flags. A parent app with subcommands would force users to type `wheeely screener` and `wheeely strategy` instead of the current direct `run-screener` / `run-strategy` commands. Separate apps match the existing pyproject.toml entry point pattern.

**Example (`scripts/run_screener.py`):**
```python
import typer
from typing import Annotated
from enum import Enum

class PresetName(str, Enum):
    conservative = "conservative"
    moderate = "moderate"
    aggressive = "aggressive"

app = typer.Typer(help="Screen stocks for wheel strategy suitability.")

@app.command()
def main(
    update_symbols: Annotated[bool, typer.Option(
        "--update-symbols",
        help="Write screened symbols to config/symbol_list.txt"
    )] = False,
    verbose: Annotated[bool, typer.Option(
        "--verbose",
        help="Show per-filter breakdown and elimination details"
    )] = False,
    preset: Annotated[PresetName | None, typer.Option(
        help="Override config preset [conservative|moderate|aggressive]"
    )] = None,
    config: Annotated[str, typer.Option(
        "--config",
        help="Path to screener config YAML file"
    )] = "config/screener.yaml",
) -> None:
    ...

# Entry point for pyproject.toml
def cli():
    app()
```

### Pattern 2: Typer Migration of run-strategy
**What:** Replace argparse in `run_strategy.py` with Typer, preserving all existing flags.
**When to use:** This is a locked decision -- must migrate.
**Key constraint:** All existing flags must work identically: `--fresh-start`, `--strat-log`, `--log-level`, `--log-to-file`. Add `--screen`.

**Example (`scripts/run_strategy.py` migration):**
```python
import typer
from typing import Annotated
from enum import Enum

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

app = typer.Typer(help="Run the options wheel trading strategy.")

@app.command()
def main(
    fresh_start: Annotated[bool, typer.Option(
        "--fresh-start",
        help="Liquidate all positions before running"
    )] = False,
    strat_log: Annotated[bool, typer.Option(
        "--strat-log",
        help="Enable strategy JSON logging"
    )] = False,
    log_level: Annotated[LogLevel, typer.Option(
        "--log-level",
        help="Set logging level",
        case_sensitive=False,
    )] = LogLevel.INFO,
    log_to_file: Annotated[bool, typer.Option(
        "--log-to-file",
        help="Write logs to file instead of just printing to stdout"
    )] = False,
    screen: Annotated[bool, typer.Option(
        "--screen",
        help="Run screener before strategy, update symbol list"
    )] = False,
) -> None:
    ...
```

### Pattern 3: Shared CLI Setup Module
**What:** Extract common initialization (credentials, logger setup) into `core/cli_common.py`.
**When to use:** Both `run-screener` and `run-strategy` need credentials and logging setup.
**Why:** Avoids duplicating credential loading and error handling.

**Example (`core/cli_common.py`):**
```python
import logging as stdlib_logging
from config.credentials import ALPACA_API_KEY, ALPACA_SECRET_KEY, IS_PAPER, require_finnhub_key
from core.broker_client import BrokerClient
from logging.logger_setup import setup_logger

def require_alpaca_credentials() -> tuple[str, str, bool]:
    """Return Alpaca credentials or raise with actionable message."""
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        raise SystemExit(
            "Error: --update-symbols requires Alpaca credentials for position protection.\n"
            "Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env"
        )
    return ALPACA_API_KEY, ALPACA_SECRET_KEY, IS_PAPER

def create_broker_client() -> BrokerClient:
    """Create BrokerClient with validated credentials."""
    key, secret, paper = require_alpaca_credentials()
    return BrokerClient(api_key=key, secret_key=secret, paper=paper)
```

### Pattern 4: Symbol Export with Position Protection
**What:** Dedicated module for safe symbol list export.
**When to use:** When `--update-symbols` is specified.
**Key logic:** Merge screened symbols with protected symbols, show colored diff, write file.

**Example (`screener/export.py`):**
```python
from pathlib import Path
from rich.console import Console

def get_protected_symbols(positions, update_state_fn) -> dict[str, str]:
    """Map symbol -> wheel state type for active positions."""
    states = update_state_fn(positions)
    return {sym: state["type"] for sym, state in states.items()}

def export_symbol_list(
    screened_symbols: list[str],
    protected: dict[str, str],
    symbol_list_path: Path,
    console: Console | None = None,
) -> None:
    """Write symbol list with position protection and diff display."""
    console = console or Console()

    # Read current list
    current = set()
    if symbol_list_path.exists():
        current = {
            line.strip() for line in symbol_list_path.read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        }

    # Build final list: screened + protected
    screened_set = set(screened_symbols)
    final = screened_set | set(protected.keys())

    # Show diff
    added = final - current
    removed = current - final
    kept_protected = set(protected.keys()) & current

    for sym in sorted(added):
        console.print(f"  [green]+{sym}[/green]")
    for sym in sorted(removed):
        console.print(f"  [red]-{sym} (screened out)[/red]")
    for sym in sorted(kept_protected):
        state_type = protected[sym].replace("_", " ")
        console.print(f"  [yellow]~{sym}: kept (active {state_type})[/yellow]")

    # Write
    symbol_list_path.write_text("\n".join(sorted(final)) + "\n")
```

### Anti-Patterns to Avoid
- **Anti-pattern: Subcommand architecture for separate tools.** Do NOT make `run-screener` and `run-strategy` subcommands of a single parent CLI. They are independent entry points with different pyproject.toml console_scripts entries.
- **Anti-pattern: Importing `logging` without alias in Typer modules.** Always use `import logging as stdlib_logging` to avoid the project's `logging/` package shadow. Typer internally uses Click which may import logging; this is handled by the project's `logging/__init__.py` re-export, but project code must be explicit.
- **Anti-pattern: Using `from __future__ import annotations` in Typer command files.** While fixed in Typer 0.9.3+ for Python >=3.10, it is unnecessary on Python 3.14 (native `X | Y` union syntax works) and historically caused issues. Avoid it in files that define Typer commands.
- **Anti-pattern: Calling `run_pipeline` inside `run-strategy --screen` without position protection.** The `--screen` flag on `run-strategy` must ALWAYS apply position protection when updating symbols, even though it auto-updates (unlike `run-screener` which defaults to `--output-only`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI parsing | Custom argparse setup | `typer.Typer()` with `Annotated` | Type-hint-driven, auto-help, auto-completion, Rich error display |
| Boolean flags | `parser.add_argument("--flag", action="store_true")` | `Annotated[bool, typer.Option("--flag")]` | Typer handles bool flags natively with `--flag/--no-flag` or `--flag`-only syntax |
| Enum choices | `choices=["DEBUG", "INFO", ...]` | `class LogLevel(str, Enum)` + Typer Option | Auto-validated, case-insensitive option, shows choices in help |
| CLI testing | Manual subprocess calls | `typer.testing.CliRunner` | Captures output, exit codes, no subprocess overhead |
| Colored terminal diff | Manual ANSI codes | Rich `console.print("[green]+NVDA[/green]")` | Already using Rich everywhere; consistent styling |

**Key insight:** Typer eliminates all CLI boilerplate. The entire argparse `core/cli_args.py` (31 lines) can be replaced by type annotations on function parameters, which are both more readable and self-documenting.

## Common Pitfalls

### Pitfall 1: logging/ Package Shadow in New Modules
**What goes wrong:** `import logging` in `scripts/run_screener.py` or any new module picks up the project's `logging/` package instead of stdlib.
**Why it happens:** Python resolves `logging` to the project's package because the project root is on `sys.path`.
**How to avoid:** Always use `import logging as stdlib_logging` in all new and modified files. The project's `logging/__init__.py` re-exports stdlib logging, so the import works but the alias makes intent clear.
**Warning signs:** `AttributeError: module 'logging' has no attribute 'getLogger'` or similar.

### Pitfall 2: Entry Point Callable vs Function
**What goes wrong:** pyproject.toml entry point `run-screener = "scripts.run_screener:main"` where `main` is a Typer-decorated function won't work correctly without the Typer app wrapper.
**Why it happens:** Typer expects `app()` to be called, not the decorated function directly.
**How to avoid:** Either point the entry to `scripts.run_screener:app` (the Typer app object which is callable) OR create a wrapper function `def cli(): app()` and point to `scripts.run_screener:cli`. The wrapper approach is more explicit and matches `run-strategy`'s existing `main()` pattern.
**Warning signs:** CLI runs but no arguments are parsed, or --help shows nothing.

### Pitfall 3: --update-symbols Without Credentials
**What goes wrong:** User runs `run-screener --update-symbols` without Alpaca .env variables set, position detection fails silently, symbols with active positions get removed.
**Why it happens:** Screener itself only needs Finnhub + Alpaca data APIs, but position protection needs the trading API.
**How to avoid:** Hard error at CLI startup if `--update-symbols` is set and Alpaca credentials are missing. Check BEFORE running the pipeline, not after. Error message: "Error: --update-symbols requires Alpaca credentials for position protection."
**Warning signs:** Missing credential check, or check happens after pipeline already ran (wasted time).

### Pitfall 4: --screen on run-strategy Changes Behavior Flow
**What goes wrong:** Adding `--screen` to `run-strategy` disrupts the existing flow (positions check, sell calls, sell puts).
**Why it happens:** The screener must run BEFORE the existing logic, and `symbol_list.txt` must be updated BEFORE it is read.
**How to avoid:** The `--screen` block runs first (with position protection), writes `symbol_list.txt`, then the existing strategy logic proceeds unchanged using the freshly-written file. The `SYMBOLS_FILE` read happens after the screen block.
**Warning signs:** Strategy using old symbol list, or screener interfering with position state.

### Pitfall 5: Typer Boolean Flag Creates --no-flag Automatically
**What goes wrong:** `--update-symbols` creates both `--update-symbols` and `--no-update-symbols`. `--output-only` creates `--no-output-only`.
**Why it happens:** Typer's default for boolean parameters is to create both positive and negative flags.
**How to avoid:** Use the explicit flag syntax: `typer.Option("--update-symbols")` to create only the positive flag. For `--output-only` which defaults True, this is actually fine since `--no-output-only` is a valid way to disable it, but consider just using `--update-symbols` as the explicit opt-in instead of having both `--output-only` and `--update-symbols`.
**Warning signs:** Help text shows unwanted `--no-*` flags.

### Pitfall 6: Zero Results from Screener Deletes All Symbols
**What goes wrong:** Screener returns 0 passing stocks, `--update-symbols` writes empty file, strategy has no symbols to trade.
**Why it happens:** No guard against empty results before export.
**How to avoid:** When zero results: print warning, skip symbol list update entirely. Use existing list. Same for `--screen` on `run-strategy`.
**Warning signs:** Empty symbol_list.txt after run.

## Code Examples

### Complete run-screener Entry Point Structure
```python
# scripts/run_screener.py
# Source: Project patterns + Typer docs
import logging as stdlib_logging
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

from config.credentials import require_finnhub_key
from screener.config_loader import ScreenerConfig, load_config
from screener.display import (
    progress_context,
    render_filter_breakdown,
    render_results_table,
    render_stage_summary,
)
from screener.pipeline import run_pipeline

logger = stdlib_logging.getLogger(__name__)


class PresetName(str, Enum):
    conservative = "conservative"
    moderate = "moderate"
    aggressive = "aggressive"


app = typer.Typer(help="Screen stocks for wheel strategy suitability.")


@app.command()
def main(
    update_symbols: Annotated[bool, typer.Option(
        "--update-symbols",
        help="Write screened symbols to config/symbol_list.txt",
    )] = False,
    verbose: Annotated[bool, typer.Option(
        "--verbose",
        help="Show per-filter breakdown waterfall",
    )] = False,
    preset: Annotated[PresetName | None, typer.Option(
        help="Override config preset [conservative|moderate|aggressive]",
    )] = None,
    config: Annotated[str, typer.Option(
        "--config",
        help="Path to screener config YAML",
    )] = "config/screener.yaml",
) -> None:
    """Screen stocks for wheel strategy suitability."""
    # 1. Load config (with optional preset override)
    # 2. Create API clients
    # 3. Run pipeline with progress callback
    # 4. Display results (table + summary, +breakdown if verbose)
    # 5. If --update-symbols: check credentials, get positions, export with protection
    ...
```

### Position-Safe Symbol Export
```python
# screener/export.py
# Source: Project patterns (state_manager.py, broker_client.py)
from pathlib import Path
from rich.console import Console
from core.state_manager import update_state

def get_protected_symbols(positions) -> dict[str, str]:
    """Detect symbols with active wheel positions.

    Returns dict mapping symbol -> state type (short_put, long_shares, short_call).
    """
    states = update_state(positions)
    return {sym: state["type"] for sym, state in states.items()}

def export_symbols(
    screened: list[str],
    protected: dict[str, str],
    path: Path,
    console: Console | None = None,
) -> bool:
    """Write symbol list, protecting active positions.

    Returns True if file was written, False if skipped (zero results).
    """
    if not screened and not protected:
        console = console or Console()
        console.print("[yellow]Warning: screener found 0 passing stocks. "
                      "Using existing symbol_list.txt.[/yellow]")
        return False

    # ... merge, diff, write logic
    return True
```

### Typer Testing Pattern
```python
# Source: Typer docs (https://typer.tiangolo.com/tutorial/testing/)
from typer.testing import CliRunner
from scripts.run_screener import app

runner = CliRunner()

def test_screener_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Screen stocks" in result.output

def test_screener_default_output_only():
    # Mock pipeline, verify no file writes
    result = runner.invoke(app, [])
    assert result.exit_code == 0

def test_update_symbols_requires_credentials():
    # With mocked missing credentials
    result = runner.invoke(app, ["--update-symbols"])
    assert result.exit_code != 0
    assert "requires Alpaca credentials" in result.output
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| argparse manual setup | Typer with Annotated syntax | Typer 0.9.0 (2023) | Less boilerplate, auto-help, type-safe |
| `typer.Option(default=X)` | `Annotated[T, typer.Option()]` | Typer 0.9.0 | Cleaner type hints, better IDE support |
| typer-slim + typer-cli | Just `typer` | 2024 | Single package, simplified install |
| Click for CLIs | Typer (built on Click) | 2020+ | Type-hint-driven API, same underlying engine |

**Deprecated/outdated:**
- `typer-cli` package: does nothing, just depends on `typer`. Use `typer` directly.
- `typer-slim` package: no longer maintained. Use `typer` directly.
- Old-style `typer.Option(default=X)` without `Annotated`: still works but `Annotated` is preferred.

## Open Questions

1. **pyproject.toml entry point format for Typer**
   - What we know: Can point to either `app` (Typer instance) or a wrapper `cli()` function.
   - What's unclear: The existing `run-strategy` uses `scripts.run_strategy:main` pointing to a regular function. After migration, `main` will be a Typer-decorated function. The entry point should point to the `app` object or a `cli` wrapper.
   - Recommendation: Use `scripts.run_screener:main` where `main = app` (assign `app` to `main`), OR create `def main(): app()` wrapper. The wrapper approach is clearest and matches existing convention. For `run-strategy`, rename the decorated function and keep `def main(): app()`.

2. **--output-only vs --update-symbols flag interaction**
   - What we know: `--output-only` is the default (display only). `--update-symbols` opts in to writing.
   - What's unclear: Are these redundant? Having `--output-only` (default True) AND `--update-symbols` (default False) means the user could technically pass both.
   - Recommendation: Treat `--update-symbols` as the only action flag. `--output-only` becomes implicit (the default behavior when `--update-symbols` is NOT passed). No need for an explicit `--output-only` flag since that is just the absence of `--update-symbols`. This satisfies CLI-04 ("accepts --output-only flag (default)") because the default behavior IS output-only.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already in use) |
| Config file | none -- no pytest.ini or pyproject.toml [tool.pytest] section |
| Quick run command | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/ -x -q` |
| Full suite command | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/ -v` |

**Note:** Tests run from `/tmp` to avoid the `logging/` package shadow on pytest import (established in Phase 1).

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLI-01 | `run-screener` command works | integration | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/test_cli_screener.py -x` | Wave 0 |
| CLI-02 | `run-strategy --screen` runs screener first | integration | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/test_cli_strategy.py -x` | Wave 0 |
| CLI-03 | `--update-symbols` writes to symbol_list.txt | unit | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/test_export.py -x` | Wave 0 |
| CLI-04 | `--output-only` default displays without modifying files | integration | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/test_cli_screener.py::test_default_no_file_writes -x` | Wave 0 |
| OUTP-03 | Export filtered symbols to symbol_list.txt | unit | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/test_export.py::test_export_writes_file -x` | Wave 0 |
| SAFE-03 | Active positions protected during export | unit | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/test_export.py::test_protected_symbols_kept -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/ -x -q`
- **Per wave merge:** `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_cli_screener.py` -- covers CLI-01, CLI-04 (Typer CliRunner tests for run-screener)
- [ ] `tests/test_cli_strategy.py` -- covers CLI-02 (Typer CliRunner tests for run-strategy --screen)
- [ ] `tests/test_export.py` -- covers CLI-03, OUTP-03, SAFE-03 (symbol export with position protection)
- [ ] `typer` package install: `uv pip install typer` -- required for all new code

## Sources

### Primary (HIGH confidence)
- [Typer official docs](https://typer.tiangolo.com/) - Package building, testing, options, callbacks, enum parameters
- [Typer PyPI](https://pypi.org/project/typer/) - Version 0.24.1, dependencies (Click, Rich, Shellingham), requires Python >=3.10
- [Typer testing docs](https://typer.tiangolo.com/tutorial/testing/) - CliRunner usage pattern
- [Typer boolean params docs](https://typer.tiangolo.com/tutorial/parameter-types/bool/) - Flag-only boolean syntax
- [Typer enum params docs](https://typer.tiangolo.com/tutorial/parameter-types/enum/) - Enum choices with Annotated syntax
- [Typer callback docs](https://typer.tiangolo.com/tutorial/commands/callback/) - Shared options pattern

### Secondary (MEDIUM confidence)
- Project codebase analysis: `scripts/run_strategy.py`, `core/cli_args.py`, `core/state_manager.py`, `screener/pipeline.py`, `screener/display.py` -- verified by reading source files
- [Typer package building tutorial](https://typer.tiangolo.com/tutorial/package/) - Entry point configuration

### Tertiary (LOW confidence)
- None -- all findings verified against official sources or project code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Typer version, API, and dependencies verified via official PyPI and docs
- Architecture: HIGH - Based on thorough analysis of existing codebase patterns and Typer official patterns
- Pitfalls: HIGH - logging shadow is a known project issue; entry point patterns verified against Typer docs; position protection logic verified against existing state_manager.py

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable domain -- CLI patterns and Typer API unlikely to change)
