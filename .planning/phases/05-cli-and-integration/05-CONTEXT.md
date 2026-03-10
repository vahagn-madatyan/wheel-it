# Phase 5: CLI and Integration - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

CLI entry points for the screener (standalone `run-screener` and `run-strategy --screen` flag), safe symbol list export with active position protection, and output mode flags (verbosity, preset override, config path). No new screening logic, no new filters, no new display components -- those are done in prior phases.

</domain>

<decisions>
## Implementation Decisions

### CLI Entry Point Design
- **Two entry points**: standalone `run-screener` command AND `run-strategy --screen` flag, both calling the same screener pipeline
- **Typer framework** for both commands -- migrate existing `run-strategy` from argparse to Typer for consistency
- New entry point: `scripts/run_screener.py` (mirrors existing `scripts/run_strategy.py` pattern)
- `pyproject.toml` gets a second `[project.scripts]` entry: `run-screener = "scripts.run_screener:main"`
- Existing `core/cli_args.py` (argparse) replaced with Typer-based CLI definitions

### Symbol Export Safety
- `--update-symbols` flag triggers writing screened symbols to `config/symbol_list.txt`
- **Active position detection** via Alpaca positions API (`BrokerClient.get_positions()`) -- same API already used by run-strategy
- Protected symbols (short puts, assigned shares, short calls) **kept in list + warning printed**: "AAPL: kept (active short put)"
- **Diff shown before writing**: "+NVDA, +AMD, -INTC (screened out)" -- no confirmation prompt, just informational
- `--update-symbols` **requires Alpaca credentials** -- hard error if missing: "requires Alpaca credentials for position protection"

### Strategy Integration Flow
- `run-strategy --screen` runs screener first, auto-updates `symbol_list.txt` (with position protection), then proceeds with strategy on the updated list
- Full Rich results table displayed even when running before strategy -- user sees what they're trading
- **Zero results handling**: warn and proceed with existing symbol list -- "Warning: screener found 0 passing stocks. Using existing symbol_list.txt."
- `--screen` and `--fresh-start` can be combined: screen first (update symbols), then fresh-start (liquidate and trade on new list)

### Output Modes and Verbosity
- **Default output** (`run-screener` with no flags): Rich results table + stage summary panel (funnel from universe to scored)
- `--output-only` is the default behavior (display results, don't modify files)
- `--verbose` adds: per-filter breakdown waterfall + per-symbol filter decisions (why each eliminated stock was removed)
- `--preset` flag: `run-screener --preset aggressive` overrides config file preset without editing screener.yaml
- `--config` flag: `run-screener --config path/to/custom.yaml` for custom config file path
- Progress bars shown during pipeline execution (already wired via `on_progress` callback from Phase 4)

### Claude's Discretion
- Typer app structure (single app vs separate apps for strategy/screener)
- How to share common CLI setup (logging, credentials) between run-strategy and run-screener
- Per-symbol verbose output formatting
- How to structure the Typer migration of run-strategy (minimal changes to existing behavior)

</decisions>

<specifics>
## Specific Ideas

- The diff output for --update-symbols should be clear: green for added symbols, red for removed, yellow for protected (active positions)
- Per-symbol filter decisions in --verbose mode should show what filter failed and the actual vs threshold value (FilterResult already has actual_value, threshold, reason fields)
- The --screen flag on run-strategy should feel seamless -- screener output appears, then strategy continues below it

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/cli_args.py`: Current argparse setup for run-strategy -- will be replaced with Typer
- `core/broker_client.py`: `BrokerClient` with `get_positions()` -- reuse for active position detection
- `core/state_manager.py`: `update_state()` maps positions to wheel states (short_put, long_shares, short_call) -- provides exact position types for protection labels
- `screener/pipeline.py`: `run_pipeline()` with all parameters already defined, including `on_progress` callback
- `screener/display.py`: `render_results_table()`, `render_stage_summary()`, `render_filter_breakdown()`, `progress_context()` -- all ready to wire
- `config/credentials.py`: Loads ALPACA_API_KEY, ALPACA_SECRET_KEY, IS_PAPER from .env

### Established Patterns
- `import logging as stdlib_logging` to avoid logging/ shadow
- Console scripts defined in pyproject.toml `[project.scripts]`
- Config loaded via `config/screener.yaml` with preset support (ScreenerConfig from config_loader.py)
- BrokerClient wraps three Alpaca SDK clients (trading, stock, options)

### Integration Points
- `scripts/run_screener.py` -- new file, parallel to `scripts/run_strategy.py`
- `pyproject.toml` [project.scripts] -- add `run-screener` entry
- `scripts/run_strategy.py` -- add `--screen` flag, import screener pipeline
- `core/cli_args.py` -- replace with Typer or delete (Typer handles CLI args)
- `config/symbol_list.txt` -- write target for --update-symbols

</code_context>

<deferred>
## Deferred Ideas

- v2 OUTP-05: Options chain preview alongside each result (best put strike, premium, delta)
- v2 OUTP-06: --dry-run mode showing what would change in symbol_list.txt
- v2 PERF-02: --verbose per-symbol filter decisions (partial implementation in v1 -- full verbose logging in v2)

</deferred>

---

*Phase: 05-cli-and-integration*
*Context gathered: 2026-03-10*
