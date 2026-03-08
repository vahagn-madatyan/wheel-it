# Wheeely Stock Screener

## What This Is

A stock screening module for the existing Wheeely options wheel strategy bot. It screens stocks using Finnhub fundamental data (market cap, debt/equity, margins, sales growth) and Alpaca real-time market data (price, volume, RSI, SMA200, options availability), outputting results as a rich table for review and optionally updating the bot's symbol list. Users configure screening criteria via a YAML config file with preset profiles (conservative, moderate, aggressive) and custom overrides.

## Core Value

Automatically identify wheel-strategy-suitable stocks by combining fundamental health checks with technical screening, replacing manual symbol selection with data-driven filtering.

## Requirements

### Validated

- ✓ Alpaca API integration for trading, stock data, and option data — existing
- ✓ CLI entry point pattern with argparse — existing
- ✓ Symbol list management via config/symbol_list.txt — existing
- ✓ BrokerClient facade over Alpaca SDK clients — existing
- ✓ Strategy parameter configuration via config/params.py — existing
- ✓ Environment-based credential management via .env — existing

### Active

- [ ] YAML-based screening config with preset profiles and custom overrides
- [ ] Finnhub API integration for fundamental screening (market cap, debt/equity, net margin, sales growth)
- [ ] Alpaca market data integration for technical screening (price range, average volume, RSI, SMA200)
- [ ] Alpaca options data integration for options availability check
- [ ] Rich table output showing screening results with scores
- [ ] Symbol list export (write filtered symbols to config/symbol_list.txt)
- [ ] Standalone `run-screener` CLI command
- [ ] `run-strategy --screen` flag to run screening before strategy execution
- [ ] Finnhub API key support in .env file (FINNHUB_API_KEY)

### Out of Scope

- Real-time streaming screener (WebSocket-based continuous monitoring) — future enhancement
- Web UI for screening results — CLI-only for now
- Backtesting screener results against historical performance — separate feature
- Finviz scraping — using Finnhub API instead for fundamental data
- Custom indicator development (MACD, Bollinger, etc.) — start with RSI and SMA200 only

## Context

The existing Wheeely bot trades a hardcoded list of symbols from `config/symbol_list.txt`. This screener adds data-driven symbol discovery. The Finviz screener URL provided as reference uses these filters:
- Market Cap: Mid and over
- Debt/Equity: Under 1
- Net Margin: Positive
- Sales Q/Q: Over 5%
- Average Volume: Over 2M
- Optionable: Yes
- Price: $10-$50
- RSI(14): Not overbought (<60)
- Price above SMA200

These map to two data sources: Finnhub (fundamentals) and Alpaca (technical/options). The screener will combine both, applying filters from the YAML config to produce a scored list of candidates.

## Constraints

- **Data Source**: Finnhub free tier has 60 calls/min rate limit — screener must respect this
- **Data Source**: Alpaca market data requires existing API keys; real-time data availability depends on subscription tier
- **Tech Stack**: Must integrate with existing Python/alpaca-py codebase; use `uv` for dependency management
- **Config Format**: YAML for screening config (not Python constants like existing params.py)
- **No Database**: Consistent with existing pattern — no persistent local storage

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Finnhub for fundamentals | Alpaca doesn't provide fundamental data; Finnhub has free tier with market cap, financials, ratios | — Pending |
| YAML config with presets | More user-friendly than raw Python constants; presets lower barrier to entry | — Pending |
| Dual CLI integration | Standalone `run-screener` + `run-strategy --screen` serves both exploration and automation | — Pending |
| Finnhub API key in .env | Consistent with existing Alpaca credential pattern | — Pending |

---
*Last updated: 2026-03-07 after initialization*
