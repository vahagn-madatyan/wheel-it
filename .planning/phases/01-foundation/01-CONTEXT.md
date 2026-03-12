# Phase 1: Foundation - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

YAML-based screening configuration with preset profiles (conservative, moderate, aggressive), Pydantic validation, ScreenedStock data model, and Finnhub API key setup in .env. No API calls, no filtering logic, no CLI entry points — those are later phases.

</domain>

<decisions>
## Implementation Decisions

### Preset Filter Values
- Finviz reference values are the **moderate** preset baseline
- Conservative is tighter on fundamentals, aggressive is looser
- **Technical filters are constant across all presets**: price $10-$50, avg volume >2M, RSI <60, price >SMA200
- Only fundamental filters vary by preset: debt/equity, net margin, sales growth, market cap thresholds
- Claude determines the specific conservative/aggressive fundamental values based on wheel strategy best practices

### Config File Structure
- Config file lives at `config/screener.yaml`
- `preset:` field at top selects the base profile (conservative, moderate, aggressive)
- Filters grouped by data source: `fundamentals:`, `technicals:`, `options:`, `sectors:`
- Example structure:
  ```yaml
  preset: moderate
  fundamentals:
    market_cap_min: 2_000_000_000
    debt_equity_max: 1.0
    net_margin_min: 0
    sales_growth_min: 5
  technicals:
    price_min: 10
    price_max: 50
    avg_volume_min: 2_000_000
    rsi_max: 60
    above_sma200: true
  options:
    optionable: true
  sectors:
    include: []  # empty = all
    exclude: ["Utilities"]
  ```
- **Deep merge**: User overrides only specified fields; all other values come from the selected preset
- Preset YAML files stored in `config/presets/` directory

### ScreenedStock Data Model
- **Full data**: Carry all fetched data (price, volume, market cap, debt/equity, margins, growth, RSI, SMA200, sector, score) plus raw Finnhub/Alpaca responses for debugging
- **Track filter results**: Each stock records pass/fail per filter — enables detailed elimination reporting in Phase 4
- **Progressive build pattern**: Start with symbol, add Alpaca data, add Finnhub data, add indicators, add score — fields are Optional until populated (mirrors existing Contract dataclass with multiple constructors)

### Error & Defaults Behavior
- **Missing screener.yaml**: Auto-generate `config/screener.yaml` with moderate preset on first run
- **Partial config**: Fill missing fields from selected preset, but **log a warning** for each field that fell back to preset defaults
- **Missing FINNHUB_API_KEY**: Hard error with clear instructions: "FINNHUB_API_KEY not found in .env. Get a free key at finnhub.io/register"
- **Invalid config values**: Pydantic validation with clear, actionable error messages (wrong types, out-of-range, missing required fields)

### Claude's Discretion
- Specific conservative and aggressive fundamental threshold values
- Pydantic model field naming conventions
- Internal structure of preset YAML files
- How to handle the `logging/` package shadow issue (flagged in STATE.md)

</decisions>

<specifics>
## Specific Ideas

- The Finviz screener URL values are the moderate baseline: market cap mid+, debt/equity <1, net margin positive, sales growth >5%, avg volume >2M, optionable, price $10-$50, RSI <60, price >SMA200
- Config file follows the grouped-by-source preview layout shown during discussion
- Progressive build pattern on ScreenedStock mirrors the existing `Contract` dataclass approach (from_contract, from_contract_snapshot constructors)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config/credentials.py`: Pattern for loading API keys from .env via python-dotenv — reuse for FINNHUB_API_KEY
- `models/contract.py`: `Contract` dataclass with multiple constructors and optional lazy update — pattern template for `ScreenedStock`
- `config/params.py`: Shows existing parameter pattern (flat Python constants) — the YAML config replaces this approach for screening

### Established Patterns
- Environment variables loaded via `python-dotenv` with `load_dotenv(override=True)`
- Dataclasses with `@dataclass` decorator and multiple class method constructors (`from_contract`, `from_contract_snapshot`, `from_dict`)
- Configuration as plain Python module imports (`from config.params import MAX_RISK`)

### Integration Points
- `config/` directory is where all configuration lives — screener.yaml and presets/ go here
- `.env` file for FINNHUB_API_KEY alongside existing ALPACA_API_KEY and ALPACA_SECRET_KEY
- `models/` directory for the ScreenedStock dataclass

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-03-07*
