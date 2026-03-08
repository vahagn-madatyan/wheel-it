# Stack Research

**Domain:** Stock Screening Module (Wheel Strategy Bot Extension)
**Researched:** 2026-03-07
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| finnhub-python | 2.4.27 | Finnhub API client for fundamental data | Only official Python SDK; provides `company_profile2()` for market cap and `company_basic_financials()` for debt/equity, margins, growth metrics. Only dependency is `requests` (already installed). |
| PyYAML | 6.0.3 | YAML config file parsing | Uncontested standard for YAML in Python. Lightweight, no external deps. |
| Pydantic | 2.x | Config validation and screening result models | Already installed via alpaca-py dependency chain. Provides typed validation for YAML config without adding new deps. |
| ta | 0.11.0 | Technical indicator calculation (RSI, SMA) | Pure Python library with clean pandas Series I/O. `RSIIndicator` and `SMAIndicator` classes verified. Depends on pandas + numpy (both already installed). |
| rich | 14.x | CLI table display and progress bars | Superior to tabulate for CLI tools. Colored tables, progress bars (useful during rate-limited screening), styled console output. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ratelimit | 2.2.1 | Decorator-based API rate limiting | Enforcing Finnhub 60 calls/min limit. Note: last release 2019 but stable. Fallback: manual `time.sleep()` wrapper (~10 lines). |
| argparse | stdlib | CLI argument parsing | Already in use for `run-strategy`. Extend for `run-screener` command. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Package management | Already used in project. `uv pip install finnhub-python pyyaml ta rich` |

## Installation

```bash
# Core screening dependencies
uv pip install finnhub-python pyyaml ta rich

# ratelimit (optional, can use manual sleep instead)
uv pip install ratelimit
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| finnhub-python | yfinance | If Finnhub rate limits are too restrictive; yfinance has no official rate limit but is web scraping (fragile) |
| ta | pandas-ta | **NEVER** — pandas-ta has been removed from PyPI |
| ta | talib (TA-Lib) | If you need 100+ indicators; requires C library installation (complex setup) |
| rich | tabulate | If you need minimal dependencies and plain text only |
| PyYAML | StrictYAML | If you want schema validation in YAML itself; unnecessary with Pydantic validation layer |
| argparse | Click/Typer | If building a large CLI with many subcommands; overkill for 2 entry points with ~5 flags each |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| pandas-ta | Removed from PyPI, no longer installable | ta 0.11.0 |
| TA-Lib (talib) | Requires C library installation, complicates setup for 2 indicators | ta 0.11.0 |
| finvizfinance | Web scraping, fragile, may break without notice | finnhub-python (proper API) |
| yfinance | Unofficial Yahoo Finance scraping, rate limits unclear, breaks periodically | finnhub-python (official API with clear rate limits) |
| Click/Typer | Migration cost for existing argparse setup; not justified for 5 flags | argparse (stdlib, already in use) |

## Stack Patterns

**Rate limit handling:**
- Finnhub free tier: 60 calls/min
- Full mid-cap+ universe scan (~500 stocks) takes ~9 minutes
- Use `rich.progress.Progress` bar to show screening progress to user

**Config validation chain:**
- YAML file → PyYAML parse → Pydantic model validation → typed config object
- Presets loaded first, then user overrides applied on top

**Logging caution:**
- The project's `logging/` package shadows Python's stdlib `logging`
- The `ta` library imports may be affected if imported from project root
- Screener module must be aware of this existing codebase quirk

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| finnhub-python 2.4.27 | requests >=2.28 | requests already installed via alpaca-py |
| ta 0.11.0 | pandas >=1.5, numpy >=1.23 | Both already declared as project dependencies |
| Pydantic 2.x | alpaca-py | Already installed as transitive dependency |
| rich 14.x | Python >=3.9 | Project already requires Python >=3.9 |

## Sources

- PyPI finnhub-python package — version and dependency verification
- PyPI ta package — RSIIndicator and SMAIndicator class verification
- Finnhub API docs (finnhub.io/docs/api) — endpoint availability and rate limits
- Existing codebase STACK.md — current dependency inventory

---
*Stack research for: Stock Screening Module*
*Researched: 2026-03-07*
