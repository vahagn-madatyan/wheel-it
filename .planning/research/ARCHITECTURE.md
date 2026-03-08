# Architecture Research

**Domain:** Stock Screening Module Integration
**Researched:** 2026-03-07
**Confidence:** HIGH

## System Structure

### New Components

The screener should be a **separate `screener/` package** that parallels `core/`, isolating all new code from the working strategy pipeline.

```
wheeely/
  core/                    # Existing — no changes except BrokerClient
    broker_client.py       # MODIFY: add get_stock_bars() for historical OHLCV
    strategy.py            # Unchanged
    execution.py           # Unchanged
    state_manager.py       # Unchanged (read by screener for position protection)
  screener/                # NEW package
    __init__.py
    config.py              # YAML config loader + Pydantic models + presets
    finnhub_client.py      # Finnhub API wrapper with rate limiting
    indicators.py          # RSI, SMA200 calculation using ta library
    filters.py             # Pure filter functions (fundamental + technical)
    scorer.py              # Wheel-suitability scoring
    runner.py              # Orchestrates the full screening pipeline
    display.py             # Rich table output + symbol list export
  config/
    symbol_list.txt        # Existing — screener can update this
    screener.yaml          # NEW — screening configuration
    presets/               # NEW — preset profiles
      conservative.yaml
      moderate.yaml
      aggressive.yaml
  scripts/
    run_strategy.py        # MODIFY: add --screen flag
    run_screener.py        # NEW entry point
  models/
    contract.py            # Existing — unchanged
    screened_stock.py      # NEW — dataclass for screening results
```

### Component Boundaries

| Component | Responsibility | Depends On | Used By |
|-----------|---------------|------------|---------|
| `screener/config.py` | Load YAML, merge presets with overrides, validate via Pydantic | PyYAML, Pydantic | runner.py |
| `screener/finnhub_client.py` | Fetch market cap, financials, basic metrics from Finnhub | finnhub-python, ratelimit | runner.py |
| `screener/indicators.py` | Compute RSI(14), SMA(200) from OHLCV bars | ta library, pandas | filters.py |
| `screener/filters.py` | Apply fundamental + technical filters to stock data | config (thresholds) | runner.py |
| `screener/scorer.py` | Score stocks for wheel suitability | filter results | runner.py |
| `screener/runner.py` | Wire components into full pipeline | All screener modules + BrokerClient | CLI entry points |
| `screener/display.py` | Rich table rendering + symbol list file export | rich, state_manager (position protection) | runner.py |
| `models/screened_stock.py` | Dataclass holding all screening data per symbol | None (pure data) | All screener modules |

## Data Flow

### Screening Pipeline

```
1. Load Config
   screener.yaml → Pydantic model → typed filter thresholds

2. Build Universe
   Alpaca: get all US stock symbols with options
   → Initial universe (~3000+ symbols)

3. Cheap Pre-Filters (Alpaca — no rate limit concern)
   Filter by: price range, average volume
   → Reduced universe (~200-500 symbols)

4. Expensive Fundamental Filters (Finnhub — 60 calls/min)
   For each remaining symbol:
     company_profile2() → market cap
     company_basic_financials() → debt/equity, net margin, sales growth
   Filter by: market cap, debt/equity, net margin, sales growth
   → Further reduced (~50-150 symbols)

5. Technical Indicator Filters (Alpaca bars — batch-friendly)
   Fetch 200-day daily bars for remaining symbols
   Compute: RSI(14), SMA(200)
   Filter by: RSI < threshold, price > SMA200
   → Final candidates (~20-50 symbols)

6. Score & Rank
   Score each candidate for wheel suitability
   Sort by score descending

7. Output
   Display rich table with results
   Optionally export to symbol_list.txt (with position protection)
```

### Key Design Principle: Filter Order Matters

The pipeline is ordered from **cheapest to most expensive** API calls:
1. Alpaca price/volume (batch, no meaningful rate limit) — eliminates ~80% of universe
2. Finnhub fundamentals (60/min rate limit) — only called on pre-filtered set
3. Alpaca bars for indicators (batch, moderate cost) — only for fundamental survivors

This ordering minimizes Finnhub API calls, keeping the screener within free tier limits for most runs.

### Integration Seams

**Screener → Strategy (file-based):**
```
run-screener --update-symbols
  → writes config/symbol_list.txt
  → run-strategy reads symbol_list.txt (existing behavior)
```

**Screener → Strategy (in-memory, --screen flag):**
```
run-strategy --screen
  → runs screening pipeline internally
  → passes symbol list directly to sell_puts()
  → no file write needed
```

### Existing Code Modifications

Only **two existing files** need modification:

1. **`core/broker_client.py`** — Add `get_stock_bars()` method for fetching historical OHLCV data (needed for RSI/SMA calculation). Follows existing pagination pattern.

2. **`scripts/run_strategy.py`** — Add `--screen` flag to argparse. When set, run screening pipeline before strategy execution and use results as symbol list.

Everything else in the existing codebase remains untouched.

## Build Order

Based on dependency analysis, components should be built in this order:

| Order | Component | Can Parallel With | Rationale |
|-------|-----------|-------------------|-----------|
| 1 | `models/screened_stock.py` + `screener/config.py` | Nothing | Data shapes and config are foundational — everything else depends on them |
| 2a | `screener/finnhub_client.py` | 2b, 2c | API client can be built independently |
| 2b | `core/broker_client.py` (add bars) | 2a, 2c | Extend existing client independently |
| 2c | `screener/indicators.py` | 2a, 2b | Pure computation, only needs bar data shape |
| 3 | `screener/filters.py` + `screener/scorer.py` | Nothing | Pure logic, depends on data shapes from step 1 |
| 4 | `screener/runner.py` | Nothing | Orchestration, wires all components |
| 5 | `screener/display.py` + CLI entry points | Nothing | Output layer, depends on runner results |

**Parallelization opportunity:** Steps 2a, 2b, and 2c have no dependencies on each other and can be developed simultaneously.

## Patterns to Follow

From existing codebase analysis:

- **Dataclass with multiple constructors**: `ScreenedStock` should mirror `Contract` pattern with `from_finnhub()` and `from_alpaca()` constructors
- **Pure filter/score functions**: Mirror `core/strategy.py` — no API calls in filter/score functions
- **Dependency injection**: Pass clients as parameters, not globals
- **No local database**: Consistent with existing pattern — all state from API calls
- **Fail-fast with ValueError**: Match existing error handling pattern

---
*Architecture research for: Stock Screening Module*
*Researched: 2026-03-07*
