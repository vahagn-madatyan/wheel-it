# Project Research Summary

**Project:** Wheeely — Stock Screening Module
**Domain:** Financial data pipeline (screener) integrated with automated options wheel strategy bot
**Researched:** 2026-03-07
**Confidence:** HIGH

## Executive Summary

This project extends an existing, working options wheel strategy bot with a stock screening module that automatically identifies the best stocks to trade the wheel on. The problem is well-defined: fetch fundamental data (market cap, debt/equity, margins, growth) and technical indicators (RSI, SMA200), filter and score stocks for wheel suitability, and output a ranked symbol list the bot already consumes. Experts build this as a staged filter pipeline ordered from cheapest to most expensive API calls, because the dominant constraint is Finnhub's 60 calls/minute free-tier rate limit.

The recommended approach is to build the screener as a separate `screener/` package that shares only the `BrokerClient` and `state_manager` with the existing codebase, requiring modifications to just two existing files. The stack is conservative and nearly zero-risk: finnhub-python for fundamental data, the `ta` library for RSI/SMA indicators (both verified on PyPI), Pydantic for config validation (already installed), and `rich` for CLI output. All new dependencies are compatible with the existing dependency tree. No database is needed — the screener is a stateless batch pipeline that reads APIs and writes a text file.

The primary risks are operational, not technical. Finnhub rate limits can silently produce incomplete results if not handled with proper rate limiting and cheap-first filter ordering. Finnhub's metric keys are inconsistent across symbols (TTM vs. Quarterly vs. Annual suffixes), requiring a fallback chain. Most critically, overwriting `symbol_list.txt` can orphan active positions — the screener must check current positions before removing any symbol from the list.

## Key Findings

### Recommended Stack

The stack is low-risk because most dependencies are already installed or have zero conflicts with the existing project. Only two genuinely new packages are needed (finnhub-python and ta), plus rich for display.

**Core technologies:**
- **finnhub-python 2.4.27**: Fundamental data (market cap, financials) — only official Finnhub SDK; sole dependency is `requests` (already installed)
- **ta 0.11.0**: Technical indicators (RSI, SMA) — pure Python with pandas/numpy I/O (both already installed). Do NOT use pandas-ta (removed from PyPI) or TA-Lib (requires C library)
- **Pydantic 2.x**: Config validation for YAML screener settings — already installed via alpaca-py dependency chain
- **PyYAML 6.0.3**: YAML config parsing — lightweight, no external dependencies
- **rich 14.x**: CLI table display and progress bars during rate-limited screening runs

**Critical version note:** pandas-ta has been removed from PyPI entirely. TA-Lib requires C library installation. The `ta` library (0.11.0) is the only viable pure-Python option for RSI/SMA.

### Expected Features

**Must have (table stakes):**
- Fundamental filters (market cap, debt/equity, net margin, sales growth) via Finnhub
- Technical filters (price range, volume, RSI(14), SMA(200)) via Alpaca bars + ta
- Options availability check via Alpaca options API
- YAML configuration with Pydantic validation
- Preset profiles (conservative, moderate, aggressive)
- CLI entry point (`run-screener`) and rich table output
- Symbol list export to `config/symbol_list.txt`
- Progress indicator during rate-limited Finnhub calls
- Filter summary showing elimination counts per stage

**Should have (differentiators):**
- Wheel-specific scoring (premium yield, assignment probability, capital efficiency)
- Active position protection when updating symbol list
- Dry-run mode (`--dry-run` flag)
- `run-strategy --screen` integration flag

**Defer (v2+):**
- Options chain preview alongside screened stocks (high complexity)
- Sector/industry diversification filter
- Custom filter expressions
- Result caching for Finnhub responses

**Do NOT build:** Real-time streaming, backtesting, web dashboard, sentiment analysis, ML-based screening, multi-broker support.

### Architecture Approach

The screener is a separate `screener/` package parallel to `core/`, isolating all new code from the working strategy pipeline. Only two existing files are modified: `broker_client.py` (add `get_stock_bars()`) and `run_strategy.py` (add `--screen` flag). The pipeline flows from config loading through universe construction, cheap Alpaca pre-filters, expensive Finnhub fundamental filters, technical indicator filters, scoring, and finally output/export. This filter ordering is not optional — it is the key architectural decision that keeps Finnhub API usage within free-tier limits.

**Major components:**
1. **screener/config.py** — YAML loading + Pydantic validation + preset merging
2. **screener/finnhub_client.py** — Finnhub API wrapper with rate limiting and metric key fallback chains
3. **screener/indicators.py** — RSI(14) and SMA(200) computation from daily OHLCV bars
4. **screener/filters.py** — Pure filter functions (no API calls, mirrors `core/strategy.py` pattern)
5. **screener/scorer.py** — Wheel-suitability scoring
6. **screener/runner.py** — Pipeline orchestration wiring all components
7. **screener/display.py** — Rich table rendering + symbol list file export with position protection
8. **models/screened_stock.py** — Dataclass for screening results (mirrors `Contract` pattern)

### Critical Pitfalls

1. **Finnhub rate limit exhaustion** — Apply cheap Alpaca filters first to reduce Finnhub calls from ~1000 to ~200. Use a token-bucket rate limiter decorator on all Finnhub methods. Show a progress bar so users know screening is active.
2. **Finnhub metric key inconsistency** — Build a fallback chain (TTM -> Quarterly -> Annual) for each metric. Treat missing metrics as "filter not applicable" (fail the filter), not "filter passed."
3. **Symbol list overwrite destroying active positions** — Read current positions via `state_manager.update_state()` before writing. Never remove symbols with active positions. Default to display-only mode; require explicit `--update-symbols` flag to write.
4. **Stale presets returning zero results** — Always show per-filter elimination counts. When zero results are returned, the filter summary tells users exactly which filter eliminated everything.
5. **Market hours data inconsistency** — Always use daily close bars (`timeframe=1Day`) with end date set to previous market close. Never use intraday data for RSI/SMA.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation (Config + Data Models)
**Rationale:** Everything depends on the config schema and data model shapes. Building these first establishes the contract for all other components.
**Delivers:** `screener/config.py`, `models/screened_stock.py`, `config/screener.yaml`, preset YAML files
**Addresses:** YAML configuration, preset profiles, Pydantic validation
**Avoids:** Stale presets pitfall (by documenting assumptions in YAML), undefined data shapes causing rework

### Phase 2: Data Sources (API Clients)
**Rationale:** The two external data sources (Finnhub and Alpaca bars) can be built in parallel and are needed by filters. This is the riskiest phase because it involves external API integration and rate limiting.
**Delivers:** `screener/finnhub_client.py`, `core/broker_client.py` extension (get_stock_bars), `screener/indicators.py`
**Uses:** finnhub-python, ta library, Alpaca SDK (existing)
**Avoids:** Finnhub rate limit exhaustion (rate limiter built into client), metric key inconsistency (fallback chain in client)

### Phase 3: Filtering + Scoring Pipeline
**Rationale:** With data sources ready, filters and scoring are pure functions that can be built and tested against real API data. These are the core logic of the screener.
**Delivers:** `screener/filters.py`, `screener/scorer.py`
**Addresses:** Fundamental filters, technical filters, wheel-specific scoring
**Avoids:** Market hours inconsistency (daily close bars only)

### Phase 4: Pipeline Orchestration
**Rationale:** The runner wires data sources, filters, and scoring into the staged pipeline. Filter ordering (cheap first) is enforced here.
**Delivers:** `screener/runner.py`
**Implements:** The cheap-to-expensive filter pipeline architecture
**Avoids:** Finnhub rate limit exhaustion (pipeline ordering)

### Phase 5: Output, CLI, and Integration
**Rationale:** Output and CLI come last because they depend on the complete pipeline. Position protection must be implemented here to avoid the most critical pitfall.
**Delivers:** `screener/display.py`, `scripts/run_screener.py`, `--screen` flag on `run-strategy`
**Addresses:** Rich table output, symbol list export, progress indicator, filter summary, CLI entry point, strategy integration
**Avoids:** Symbol list overwrite destroying active positions (position protection logic)

### Phase Ordering Rationale

- **Config and models first** because every other component depends on data shapes and filter thresholds
- **Data sources before filters** because filters consume data from these sources; building them second allows early detection of API integration issues (the highest-risk area)
- **Filters before orchestration** because pure filter logic can be validated independently before wiring into a pipeline
- **Output last** because it is the lowest-risk component and depends on everything else being complete
- **Position protection in the final phase** because it requires access to the existing `state_manager`, which is an integration concern best handled when the full pipeline is working

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Data Sources):** Finnhub API response shapes and metric key variations need hands-on exploration. The exact fallback key chains should be validated against real API responses for 10-20 diverse symbols. Alpaca's `get_stock_bars` API for multi-symbol batch requests may have undocumented pagination behavior.
- **Phase 5 (Output + Integration):** The `state_manager.update_state()` integration for position protection needs careful examination of what data it returns and how to map it to symbol protection logic.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** YAML + Pydantic config loading is well-documented; preset files are just YAML with predefined values.
- **Phase 3 (Filtering + Scoring):** Pure filter functions following the existing `core/strategy.py` pattern. Standard comparisons against thresholds.
- **Phase 4 (Orchestration):** Straightforward pipeline wiring, following the existing `core/execution.py` pattern.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All packages verified on PyPI. Dependency compatibility confirmed against existing project. No version conflicts. |
| Features | HIGH | Feature set derived from wheel strategy domain requirements and existing codebase analysis. Clear table stakes vs. differentiators. |
| Architecture | HIGH | Module structure mirrors existing codebase patterns. Only 2 existing files modified. Clean separation of concerns. |
| Pitfalls | MEDIUM-HIGH | Rate limiting and position protection pitfalls are well-understood. Finnhub metric key inconsistency needs hands-on validation to build exact fallback chains. |

**Overall confidence:** HIGH

### Gaps to Address

- **Finnhub metric key mapping:** The exact camelCase keys and suffix variants (TTM, Quarterly, Annual, 5Y) need to be cataloged by querying the API for a diverse set of symbols. This should be done early in Phase 2 before building the fallback chain.
- **Alpaca multi-symbol bar requests:** Whether Alpaca supports fetching bars for multiple symbols in a single request (vs. one-by-one) needs API verification. This affects performance significantly for 200+ symbols in Phase 2.
- **Universe construction source:** How to get the initial list of all US optionable stocks is not fully specified. Alpaca's asset listing API with `status=active` and `asset_class=us_equity` is the likely approach, but options availability filtering specifics need validation.
- **The `logging/` shadow:** Whether the `ta` and `finnhub-python` libraries break when imported from the project root needs a quick test early in Phase 1. If they do, a fix should be applied before building anything else.

## Sources

### Primary (HIGH confidence)
- PyPI package pages — finnhub-python 2.4.27, ta 0.11.0, rich 14.x version and dependency verification
- Finnhub API documentation (finnhub.io/docs/api) — endpoint availability, rate limits (60/min free tier)
- Existing codebase analysis — `core/`, `models/`, `config/`, `scripts/` module patterns and dependencies
- Alpaca SDK documentation — options and stock data API capabilities

### Secondary (MEDIUM confidence)
- Finnhub metric key naming conventions — inferred from API documentation, needs live validation
- Alpaca multi-symbol bar request behavior — inferred from SDK patterns, not directly tested

---
*Research completed: 2026-03-07*
*Ready for roadmap: yes*
