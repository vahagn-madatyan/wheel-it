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



## Validated

### HVPR-01 — User can filter stocks by HV Percentile rank (30-day HV percentile over 252-day lookback)

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S08
- Proof: 7 computation tests + 2 Stage 1 integration tests in test_hv_earnings.py

### HVPR-02 — HV Percentile threshold is configurable per preset (conservative>=50, moderate>=30, aggressive>=20)

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S08
- Proof: 3 preset YAML tests + 1 differentiation test in test_hv_earnings.py

### HVPR-03 — HV Percentile value is displayed in screener results table

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S08
- Proof: HV%ile column added to render_results_table(); display tests pass

### EARN-01 — User can filter stocks that have earnings within N days (default 14)

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S08
- Proof: 8 filter boundary tests in test_hv_earnings.py

### EARN-02 — Earnings data is fetched via Finnhub earnings calendar endpoint (free tier)

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S08
- Proof: 5 FinnhubClient earnings tests (mocked) in test_hv_earnings.py

### EARN-03 — Earnings day threshold is configurable per preset (conservative>=21, moderate>=14, aggressive>=7)

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S08
- Proof: 3 preset YAML tests + 1 differentiation test in test_hv_earnings.py

### OPTS-01 — User can filter stocks by options chain OI (minimum open interest on nearest ATM put)

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S09
- Proof: 7 filter_options_oi tests + run_stage_3_options integration tests in test_options_chain.py

User can filter stocks by options chain OI (minimum open interest on nearest ATM put)

### OPTS-02 — User can filter stocks by bid/ask spread (maximum spread on nearest ATM put)

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S09
- Proof: 6 filter_options_spread tests + run_stage_3_options integration tests in test_options_chain.py

User can filter stocks by bid/ask spread (maximum spread on nearest ATM put)

### OPTS-03 — OI and spread thresholds are configurable per preset

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S09
- Proof: 5 preset threshold tests (3 per-preset + 1 differentiation + 1 strictness ordering) in test_options_chain.py

OI and spread thresholds are configurable per preset

### OPTS-04 — Options chain validation runs only on stocks that pass all prior filter stages

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S09
- Proof: test_stage3_only_for_stage2_passers in test_options_chain.py — FAIL stock has no options_oi/options_spread filter results

Options chain validation runs only on stocks that pass all prior filter stages

### OPTS-05 — Best put premium (annualized yield) is displayed in screener results table for each passing stock

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S09
- Proof: test_yield_column_in_results_table + 8 compute_put_premium_yield math tests in test_options_chain.py

Best put premium (annualized yield) is displayed in screener results table for each passing stock

### CALL-01 — User can run `run-call-screener` standalone CLI to screen covered call opportunities

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S10
- Proof: 3 CLI tests in test_call_screener.py (test_cli_invokes_screen_calls, test_cli_symbol_uppercased, test_cli_preset_override); `run-call-screener` registered in pyproject.toml

### CALL-02 — Call screener accepts symbol + cost basis (from Alpaca positions or user input) and finds best call to sell

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S10
- Proof: test_basic_screening_returns_recommendation + test_sorted_by_annualized_return_descending in test_call_screener.py; screen_calls() accepts symbol + cost_basis args

### CALL-03 — Call screener enforces strike >= cost basis (never sell below cost basis)

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S10
- Proof: test_strike_below_cost_basis_excluded + test_strike_equal_to_cost_basis_included + test_all_below_cost_basis_returns_empty in test_call_screener.py

### CALL-04 — Call screener applies same DTE/OI/spread/delta filters as put screening (configurable via presets)

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S10
- Supporting Slices: S09
- Proof: test_low_oi_excluded, test_wide_spread_excluded, test_delta_below_min_excluded, test_delta_above_max_excluded, test_preset_thresholds_applied, test_conservative_rejects_moderate_oi in test_call_screener.py; DTE range matches put screener (14-60 days)

### CALL-05 — Call screener displays Rich table with symbol, cost basis, recommended strike, DTE, premium, delta, annualized return

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S10
- Proof: test_table_renders_with_data verifies all columns present; test_table_delta_none_shows_na, test_table_empty_shows_message, test_table_multiple_rows in test_call_screener.py

### CALL-06 — `run-strategy` integrates call screener to select covered calls for assigned positions

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S10
- Proof: test_long_shares_triggers_call_screener, test_no_recommendations_does_not_sell, test_insufficient_shares_skips_call_screening in test_call_screener.py; run_strategy.py imports and uses screen_calls for long_shares state

## Deferred

## Out of Scope
