# Pitfalls Research

**Domain:** Stock Screening Module
**Researched:** 2026-03-07
**Confidence:** MEDIUM-HIGH

## Critical Pitfalls

### 1. Finnhub Rate Limit Exhaustion

**Risk Level:** HIGH
**Phase Impact:** Phase 2 (Data Sources), Phase 4 (Orchestration)

**The Problem:** Finnhub free tier allows 60 API calls/minute. Each symbol requires 2 calls (`company_profile2` + `company_basic_financials`). Screening 500 symbols = 1000 calls = ~17 minutes. Without proper rate limiting, the API returns 429 errors and silently drops data.

**Warning Signs:**
- HTTP 429 responses from Finnhub
- Inconsistent screening results between runs
- Screening taking much longer than expected

**Prevention:**
- **Order pipeline: cheap filters first.** Apply Alpaca price/volume filters (no meaningful rate limit) before Finnhub calls. This typically eliminates 80%+ of the universe, reducing Finnhub calls from 1000 to ~200 (3-4 minutes).
- Use a token-bucket rate limiter decorator on all Finnhub client methods
- Show `rich.progress.Progress` bar so users know screening is working, not stuck
- Consider caching Finnhub responses for repeat runs within same session

### 2. Finnhub Metric Key Inconsistency

**Risk Level:** HIGH
**Phase Impact:** Phase 2 (Data Sources)

**The Problem:** Finnhub's `company_basic_financials` endpoint returns a `metric` dict with camelCase keys that have TTM/Quarterly/Annual suffixes. These vary by symbol — some stocks have `netProfitMarginTTM`, others have `netProfitMarginAnnual`, some have neither. Hardcoding a single key name will silently produce null values for many symbols.

**Warning Signs:**
- Many symbols passing fundamental filters with null values
- Different screening results for the same symbol on different days
- KeyError exceptions during screening

**Prevention:**
- Build a **metric mapping layer** with fallback chains: try TTM first, then Quarterly, then Annual
- Implement null-safe access — treat missing metrics as "filter not applicable" rather than "filter passed"
- Log when fallback keys are used, so users know data quality varies
- Add a `--verbose` flag that shows which metrics were available vs. missing per symbol

### 3. Symbol List Overwrite Destroying Active Positions

**Risk Level:** CRITICAL
**Phase Impact:** Phase 5 (Output + CLI)

**The Problem:** If `run-screener --update-symbols` replaces `config/symbol_list.txt` and removes a symbol the bot currently has a short put or assigned shares on, the next `run-strategy` run will not manage that position. The bot won't sell covered calls on assigned shares or track expiring puts.

**Warning Signs:**
- Positions appearing in Alpaca but not being managed by the bot
- Assigned shares sitting without covered calls being sold
- Users losing track of existing positions

**Prevention:**
- **Active position protection:** Before writing symbol_list.txt, read current positions via `state_manager.update_state()`. Never remove symbols that have active positions.
- Warn user when a screened-out symbol has an active position: "AAPL removed from screener results but kept in symbol list (active short_put position)"
- Add `--force` flag to override protection (for advanced users who know what they're doing)
- Default `run-screener` to `--output-only` (display results without updating file)

### 4. Stale Presets Silently Filtering Everything

**Risk Level:** MEDIUM
**Phase Impact:** Phase 1 (Config)

**The Problem:** Market conditions change. A preset with `price_max: 50` and `rsi_max: 60` might return 30 stocks in a calm market but 0 stocks after a correction. Users won't know why the screener returns empty results.

**Warning Signs:**
- Screener returning 0 results with no explanation
- Users confused about why known good stocks aren't appearing
- Presets becoming unusable during market regime changes

**Prevention:**
- Implement `--dry-run` mode showing per-filter elimination counts: "Universe: 3000 → Price filter: 800 → Volume filter: 200 → Fundamentals: 50 → RSI: 0 (all eliminated)"
- Always show the filter summary even in normal mode
- Document preset assumptions in the YAML files themselves
- Consider adding a "relaxed" mode that widens filters by 20% when 0 results found

### 5. Market Hours vs. After-Hours Data Inconsistency

**Risk Level:** MEDIUM
**Phase Impact:** Phase 3 (Technical Indicators)

**The Problem:** Running the screener during market hours vs. after hours produces different RSI and SMA values because intraday bars include partial day data. This makes screening results non-reproducible and confusing.

**Warning Signs:**
- Same symbol passing RSI filter at 9am but failing at 2pm
- Different results when running screener on weekend vs. weekday evening
- Users unable to reproduce screening results

**Prevention:**
- **Always use daily close bars** for technical indicator calculation, never intraday
- Use Alpaca's `timeframe=1Day` with `end` parameter set to previous market close
- Document that technical indicators use daily close data only
- Show the data date in the output table so users know what data the indicators are based on

### 6. The `logging/` Package Shadow

**Risk Level:** LOW (but annoying)
**Phase Impact:** Phase 1 (Foundation)

**The Problem:** The project's `logging/` directory shadows Python's stdlib `logging` module. The `ta` library and `finnhub-python` both use stdlib `logging` internally. If imports happen from the project root, these libraries may fail to initialize their loggers correctly.

**Warning Signs:**
- ImportError or AttributeError related to logging
- Missing log output from ta or finnhub libraries
- Confusing error messages about missing logging attributes

**Prevention:**
- Ensure the `screener/` package imports are structured correctly
- Test that `import ta` and `import finnhub` work correctly when run from the project root
- If issues arise, use absolute imports or adjust sys.path

## Integration Gotchas

| Gotcha | Impact | Mitigation |
|--------|--------|------------|
| Alpaca `get_stock_bars()` returns different fields than `get_option_snapshot()` | Medium — schema mismatch | Use dedicated `ScreenedStock` dataclass, not `Contract` |
| Finnhub returns market cap in different currencies | Low — USD-only stocks | Filter by US exchanges only in universe construction |
| `ta` library requires pandas DataFrame with specific column names | Low — data transformation | Map Alpaca bar fields to ta's expected column names (open, high, low, close, volume) |
| `rich` table width exceeds terminal width for many columns | Low — display issue | Use `rich.console.Console(width=...)` or truncate columns |

## Performance Traps

| Trap | Expected Impact | Prevention |
|------|----------------|------------|
| Fetching Finnhub data for entire universe before filtering | 17+ min for 500 symbols | Apply Alpaca price/volume filters first |
| Fetching 200-day bars one symbol at a time | Slow, many API calls | Use Alpaca's multi-symbol bar request |
| Computing RSI for entire bar history | Unnecessary computation | Only compute on last 14 periods (+ warmup) |
| Not caching Finnhub responses between runs | Repeated 17-min waits | Optional file-based cache with TTL |

---
*Pitfalls research for: Stock Screening Module*
*Researched: 2026-03-07*
