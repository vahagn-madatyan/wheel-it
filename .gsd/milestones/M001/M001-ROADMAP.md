# M001: Migration

**Vision:** A stock screening module for the Wheeely options wheel strategy bot.

## Success Criteria


## Slices

- [x] **S01: Foundation** `risk:medium` `depends:[]`
  > After this: Create the YAML config loading pipeline with preset profiles, Pydantic validation, and the ScreenedStock data model.
- [x] **S02: Data Sources** `risk:medium` `depends:[S01]`
  > After this: Build a rate-limited Finnhub API client that fetches company profile and basic financials, handles 429 errors with retry/skip logic, and extracts metric values through fallback key chains for missing data resilience.
- [x] **S03: Screening Pipeline** `risk:medium` `depends:[S02]`
  > After this: Implement all 10 screening filter functions, historical volatility computation, and add the hv_30 field to ScreenedStock.
- [x] **S04: Output And Display** `risk:medium` `depends:[S03]`
  > After this: Create the screener display module with Rich-formatted results table and filter elimination summaries.
- [x] **S05: Cli And Integration** `risk:medium` `depends:[S04]`
  > After this: Create the symbol export module with position-safe merge logic and the shared CLI helpers that both `run-screener` and `run-strategy` will use.
- [x] **S06: Packaging Cleanup** `risk:medium` `depends:[S05]`
  > After this: Fix all four tech debt items identified in the v1.
- [ ] **S07: Pipeline Fix + Preset Overhaul** `risk:medium` `depends:[S06]`
  > After this: unit tests prove Pipeline Fix + Preset Overhaul works
- [ ] **S08: HV Rank + Earnings Calendar** `risk:medium` `depends:[S07]`
  > After this: unit tests prove HV Rank + Earnings Calendar works
- [ ] **S09: Options Chain Validation** `risk:medium` `depends:[S08]`
  > After this: unit tests prove Options Chain Validation works
- [ ] **S10: Covered Call Screening** `risk:medium` `depends:[S09]`
  > After this: unit tests prove Covered Call Screening works
