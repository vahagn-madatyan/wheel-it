# Requirements

## Active

### FIX-01 — Screener produces non-zero results when run with moderate preset against live market data

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S07

Screener produces non-zero results when run with moderate preset against live market data

### FIX-02 — Finnhub debt/equity values are normalized correctly (percentage-to-ratio conversion if needed, verified with diagnostic script)

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S07

Finnhub debt/equity values are normalized correctly (percentage-to-ratio conversion if needed, verified with diagnostic script)

### FIX-03 — Missing Finnhub data (None values) for any single metric does not eliminate a stock -- stock passes filter with neutral score instead

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S07

Missing Finnhub data (None values) for any single metric does not eliminate a stock -- stock passes filter with neutral score instead

### FIX-04 — avg_volume_min is differentiated across presets (conservative=1M, moderate=500K, aggressive=200K)

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S07

avg_volume_min is differentiated across presets (conservative=1M, moderate=500K, aggressive=200K)

### PRES-01 — All three presets differ across ALL filter categories (fundamentals, technicals, options, earnings)

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S07

All three presets differ across ALL filter categories (fundamentals, technicals, options, earnings)

### PRES-02 — Conservative preset uses tighter thresholds (large-cap, low delta, high OI, strict spread)

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S07

Conservative preset uses tighter thresholds (large-cap, low delta, high OI, strict spread)

### PRES-03 — Aggressive preset uses looser thresholds (small-cap OK, wider delta range, lower OI minimum)

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S07

Aggressive preset uses looser thresholds (small-cap OK, wider delta range, lower OI minimum)

### PRES-04 — Each preset includes default sector avoid/prefer lists (conservative favors stable sectors, aggressive excludes nothing)

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S07

Each preset includes default sector avoid/prefer lists (conservative favors stable sectors, aggressive excludes nothing)

### HVPR-01 — User can filter stocks by HV Percentile rank (30-day HV percentile over 252-day lookback)

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S08

User can filter stocks by HV Percentile rank (30-day HV percentile over 252-day lookback)

### HVPR-02 — HV Percentile threshold is configurable per preset (conservative>=50, moderate>=30, aggressive>=20)

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S08

HV Percentile threshold is configurable per preset (conservative>=50, moderate>=30, aggressive>=20)

### HVPR-03 — HV Percentile value is displayed in screener results table

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S08

HV Percentile value is displayed in screener results table

### EARN-01 — User can filter stocks that have earnings within N days (default 14)

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S08

User can filter stocks that have earnings within N days (default 14)

### EARN-02 — Earnings data is fetched via Finnhub earnings calendar endpoint (free tier)

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S08

Earnings data is fetched via Finnhub earnings calendar endpoint (free tier)

### EARN-03 — Earnings day threshold is configurable per preset (conservative>=21, moderate>=14, aggressive>=7)

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S08

Earnings day threshold is configurable per preset (conservative>=21, moderate>=14, aggressive>=7)

### OPTS-01 — User can filter stocks by options chain OI (minimum open interest on nearest ATM put)

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S09

User can filter stocks by options chain OI (minimum open interest on nearest ATM put)

### OPTS-02 — User can filter stocks by bid/ask spread (maximum spread on nearest ATM put)

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S09

User can filter stocks by bid/ask spread (maximum spread on nearest ATM put)

### OPTS-03 — OI and spread thresholds are configurable per preset

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S09

OI and spread thresholds are configurable per preset

### OPTS-04 — Options chain validation runs only on stocks that pass all prior filter stages

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S09

Options chain validation runs only on stocks that pass all prior filter stages

### OPTS-05 — Best put premium (annualized yield) is displayed in screener results table for each passing stock

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S09

Best put premium (annualized yield) is displayed in screener results table for each passing stock

### CALL-01 — User can run `run-call-screener` standalone CLI to screen covered call opportunities

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S10

User can run `run-call-screener` standalone CLI to screen covered call opportunities

### CALL-02 — Call screener accepts symbol + cost basis (from Alpaca positions or user input) and finds best call to sell

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S10

Call screener accepts symbol + cost basis (from Alpaca positions or user input) and finds best call to sell

### CALL-03 — Call screener enforces strike >= cost basis (never sell below cost basis)

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S10

Call screener enforces strike >= cost basis (never sell below cost basis)

### CALL-04 — Call screener applies same DTE/OI/spread/delta filters as put screening (configurable via presets)

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S10
- Supporting Slices: S09

Call screener applies same DTE/OI/spread/delta filters as put screening (configurable via presets)

### CALL-05 — Call screener displays Rich table with symbol, cost basis, recommended strike, DTE, premium, delta, annualized return

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S10

Call screener displays Rich table with symbol, cost basis, recommended strike, DTE, premium, delta, annualized return

### CALL-06 — `run-strategy` integrates call screener to select covered calls for assigned positions

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S10

`run-strategy` integrates call screener to select covered calls for assigned positions

## Validated

## Deferred

## Out of Scope
