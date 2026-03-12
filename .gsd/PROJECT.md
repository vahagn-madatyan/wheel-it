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

(Defined in REQUIREMENTS.md for v1.1)

### Out of Scope

- Real-time streaming screener (WebSocket-based continuous monitoring) — batch screening sufficient for wheel strategy
- Web UI for screening results — CLI-only tool
- Backtesting screener results against historical performance — separate domain
- Finviz scraping — using Finnhub API instead for reliable fundamental data
- Custom indicator development (MACD, Bollinger, etc.) — RSI and SMA200 sufficient for v1.0
- AI/ML screening — rule-based filters are transparent and debuggable
- Multi-broker support — only Alpaca is used

## Current Milestone: v1.1 Screener Fix + Covered Calls

**Goal:** Debug and fix the stock screening pipeline (zero stocks survive filtering), then add covered call screening for the wheel's second leg.

**Target features:**
- Diagnose and fix why the filter pipeline eliminates all stocks (debt_equity kills all 202 Stage 1 survivors, avg_volume at 2M is too aggressive)
- Add IV Rank approximation using free data (historical volatility proxy)
- Add earnings calendar check (free API)
- Add options chain OI & bid/ask spread filtering
- Add covered call screening (standalone `run-call-screener` CLI + integrated into `run-strategy`)
- Update preset profiles with proper filter strictness differentiation
- Add sector avoid/prefer lists to presets

## Context

Shipped v1.0 with 5,843 LOC Python across 6 phases (12 plans).
Tech stack: Python 3.13, alpaca-py, finnhub-python, ta, pydantic, rich, typer, pyyaml.
193 tests passing, zero failures. 28/28 requirements satisfied.

The screener combines Finnhub fundamentals and Alpaca technical data through a 3-stage pipeline (cheap Alpaca filters first, expensive Finnhub filters second, scoring third) to minimize API calls while respecting Finnhub's 60 calls/min rate limit.

**v1.0 screening issue:** Running the screener produces zero results. The filter breakdown shows debt_equity removes ALL 202 Stage 1 survivors (possible Finnhub data issue or threshold mismatch). avg_volume at 2M also kills 10,758 stocks. The user has a working separate screener with a detailed strategy reference document defining proper thresholds and a multi-step screening approach (Finviz-style → IV Rank → Earnings → OI/Spread → Sector Diversification → Final Options Check).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Finnhub for fundamentals | Alpaca doesn't provide fundamental data; Finnhub free tier covers market cap, financials, ratios | ✓ Good — reliable data, rate limiting works well |
| YAML config with presets | More user-friendly than raw Python constants; presets lower barrier to entry | ✓ Good — 3 presets ship with sensible defaults |
| Dual CLI integration | Standalone `run-screener` + `run-strategy --screen` serves both exploration and automation | ✓ Good — both paths work end-to-end |
| Finnhub API key in .env | Consistent with existing Alpaca credential pattern | ✓ Good |
| Cheap-first pipeline ordering | Alpaca filters (free, fast) before Finnhub filters (rate-limited) | ✓ Good — minimizes API calls |
| Pydantic v2 for config validation | Type safety + clear error messages via format_validation_errors | ✓ Good — Rich Panel UX for errors |
| Typer for CLI | Replaces argparse; flag definitions cleaner, built-in help | ✓ Good — both CLIs migrated |
| Position-safe export | Union of screened + protected symbols prevents removing active wheel positions | ✓ Good — critical safety feature |
| TDD for filter/scoring code | Red-green cycle ensures correctness of scoring math and filter logic | ✓ Good — 60 filter tests, 9 scoring tests |

| Debug first, then rebuild | User wants to understand why current pipeline fails before adding new features | — Pending |
| Free APIs only | Approximate IV Rank from HV, use free earnings APIs instead of paid Barchart/ORATS | — Pending |
| Filter strictness presets | Conservative/moderate/aggressive change thresholds, not strategy structure | — Pending |
| Covered call CLI: both modes | Standalone `run-call-screener` + integrated into `run-strategy` flow | — Pending |

---
*Last updated: 2026-03-11 after v1.1 milestone start*
