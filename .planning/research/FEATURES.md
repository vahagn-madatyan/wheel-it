# Features Research

**Domain:** Stock Screening for Wheel Strategy
**Researched:** 2026-03-07
**Confidence:** HIGH

## Feature Categories

### Table Stakes (Must Have)

These are expected in any stock screener. Without them, the tool is not useful.

| Feature | Complexity | Dependencies | Description |
|---------|-----------|--------------|-------------|
| Fundamental filters | Medium | Finnhub API | Market cap, debt/equity, net margin, sales growth — the core financial health checks |
| Technical filters | Medium | Alpaca bars + ta library | Price range, average volume, RSI(14), SMA200 — momentum and trend filters |
| Options availability check | Low | Alpaca options API | Verify stocks are optionable before including in results |
| YAML configuration | Medium | PyYAML + Pydantic | User-editable filter thresholds in a config file |
| Preset profiles | Low | Config layer | Conservative/moderate/aggressive presets so users don't start from zero |
| CLI entry point | Low | argparse | `run-screener` command to run screening independently |
| Rich table output | Medium | rich library | Formatted results table with symbol, price, volume, scores, and filter pass/fail |
| Symbol list export | Low | File I/O | Write filtered symbols to config/symbol_list.txt for strategy consumption |
| Progress indicator | Low | rich.progress | Show screening progress during rate-limited API calls (Finnhub takes ~9 min for 500 symbols) |
| Filter summary | Low | Display logic | Show how many symbols were eliminated at each filter stage |

### Differentiators (Nice to Have)

These add value but aren't required for a functional v1.

| Feature | Complexity | Dependencies | Description |
|---------|-----------|--------------|-------------|
| Wheel-specific scoring | Medium | Strategy logic | Score stocks by wheel suitability: premium yield potential, assignment probability, capital efficiency |
| Options chain preview | High | Alpaca options API | Show best put candidates (strike, premium, delta) alongside each screened stock |
| Active position protection | Low | State manager | Prevent symbol list export from removing symbols the bot is currently trading |
| Dry-run mode | Low | Display logic | Show screening results without updating symbol list (`--dry-run` flag) |
| Strategy integration | Low | CLI args | `run-strategy --screen` flag to auto-screen before trading |
| Sector/industry filter | Low | Finnhub profile | Filter by GICS sector to ensure diversification |
| Custom filter expressions | High | Expression parser | User-defined filter logic beyond predefined fields |
| Result caching | Medium | File/memory cache | Cache Finnhub responses to avoid repeated API calls within a session |

### Anti-Features (Do NOT Build)

| Feature | Why Not |
|---------|---------|
| Real-time streaming screener | Adds WebSocket complexity, rate limit issues; batch screening is sufficient for wheel strategy (trades happen weekly, not intraday) |
| Backtesting engine | Completely separate domain; would double project scope |
| Web dashboard | Out of scope; this is a CLI tool |
| Social sentiment analysis | Unreliable signal, adds API dependencies, not relevant to fundamental wheel criteria |
| AI/ML-based screening | Over-engineering; rule-based filters are transparent and debuggable |
| Multi-broker support | Only Alpaca is used; abstracting brokers adds complexity for no current value |
| Alert/notification system | Future feature; screener runs on-demand, not continuously |

## Feature Dependencies

```
YAML Config + Presets
    |
    v
Fundamental Filters (Finnhub) ──┐
                                 ├──> Scoring ──> Rich Table Output ──> Symbol Export
Technical Filters (Alpaca) ─────┘
    |
    v
Options Availability Check
```

- Fundamental and technical filters can be developed independently
- Scoring depends on filter results
- Output depends on scoring
- Symbol export depends on output + active position protection

## Wheel Strategy Specific Considerations

Stock screening for wheel strategy has unique requirements vs. general stock screening:

1. **Price range matters for capital efficiency**: $10-$50 stocks allow diversified put selling with moderate capital
2. **Options liquidity is critical**: High open interest and tight bid-ask spreads required for premium collection
3. **Low volatility preferred**: RSI < 60 and price > SMA200 indicate stable uptrend — ideal for put selling
4. **Fundamental health prevents assignment losses**: Strong financials mean assigned shares are worth holding
5. **Diversification across sectors**: Avoid concentrating all puts in one sector

---
*Features research for: Stock Screening Module*
*Researched: 2026-03-07*
