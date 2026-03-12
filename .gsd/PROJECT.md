# Wheeely Stock Screener

## What This Is

A stock screening module for the Wheeely options wheel strategy bot. Screens stocks using Finnhub fundamental data (market cap, debt/equity, margins, sales growth) and Alpaca market data (price, volume, RSI, SMA200, options availability), then scores and ranks candidates for wheel suitability. Results display as a Rich table with color-coded scores, filter elimination summaries, and progress indicators. Users configure screening via YAML presets (conservative/moderate/aggressive) with custom overrides. Integrates as standalone `run-screener` CLI and `run-strategy --screen` flag.

## Core Value

Automatically identify wheel-strategy-suitable stocks by combining fundamental health checks with technical screening, replacing manual symbol selection with data-driven filtering.

## Requirements

### Validated

- ✓ Alpaca API integration for trading, stock data, and option data — existing
- ✓ CLI entry point pattern with Typer — v1.0
- ✓ Symbol list management via config/symbol_list.txt — existing
- ✓ BrokerClient facade over Alpaca SDK clients — existing
- ✓ Strategy parameter configuration via config/params.py — existing
- ✓ Environment-based credential management via .env — existing
- ✓ YAML-based screening config with preset profiles and custom overrides — v1.0 (CONF-01..04)
- ✓ Finnhub API integration with rate limiting and fallback chains — v1.0 (SAFE-01, SAFE-02, SAFE-04)
- ✓ Alpaca market data for technical screening (RSI, SMA200, volume) — v1.0 (FILT-05..08)
- ✓ 10 screening filters with cheap-first pipeline ordering — v1.0 (FILT-01..10)
- ✓ Wheel suitability scoring with 3 weighted components — v1.0 (SCOR-01, SCOR-02)
- ✓ Rich table output with color-coded scores and filter summaries — v1.0 (OUTP-01, OUTP-02)
- ✓ Progress indicators during rate-limited API calls — v1.0 (OUTP-04)
- ✓ Position-safe symbol list export — v1.0 (OUTP-03, SAFE-03)
- ✓ Standalone `run-screener` CLI and `run-strategy --screen` integration — v1.0 (CLI-01..04)
- ✓ Human-readable config validation errors (Rich Panels) — v1.0 (Phase 6)
- ✓ Complete pyproject.toml dependency declarations — v1.0 (Phase 6)

### Active

(Defined in REQUIREMENTS.md for v1.1 — 25 requirements across FIX, PRES, HVPR, EARN, OPTS, CALL categories)

### Out of Scope

- Real-time streaming screener (WebSocket-based continuous monitoring) — batch screening sufficient for wheel strategy
- Web UI for screening results — CLI-only tool
- Backtesting screener results against historical performance — separate domain
- Finviz scraping — using Finnhub API instead for reliable fundamental data
- Custom indicator development (MACD, Bollinger, etc.) — RSI and SMA200 sufficient for v1.0
- AI/ML screening — rule-based filters are transparent and debuggable
- Multi-broker support — only Alpaca is used

## Current Milestone: M001 — Screener Fix + Covered Calls

**Goal:** Debug and fix the stock screening pipeline (zero stocks survive filtering), then add covered call screening for the wheel's second leg.

**Status:** S01–S06 complete (v1.0 shipped). S07–S10 planned (v1.1 in progress).

## Context

Shipped v1.0 with 5,843 LOC Python across 6 phases (12 plans).
Tech stack: Python 3.13, alpaca-py, finnhub-python, ta, pydantic, rich, typer, pyyaml.
193 tests passing, zero failures. 28/28 v1.0 requirements satisfied.

**v1.0 screening issue:** Running the screener produces zero results. The filter breakdown shows debt_equity removes ALL 202 Stage 1 survivors (possible Finnhub data issue or threshold mismatch). avg_volume at 2M also kills 10,758 stocks.

---
*Last updated: 2026-03-11 after M001 roadmap planning*
