# S03: Screening Pipeline

**Goal:** Implement all 10 screening filter functions, historical volatility computation, and add the hv_30 field to ScreenedStock.
**Demo:** Implement all 10 screening filter functions, historical volatility computation, and add the hv_30 field to ScreenedStock.

## Must-Haves


## Tasks

- [x] **T01: 03-screening-pipeline 01** `est:3min`
  - Implement all 10 screening filter functions, historical volatility computation, and add the hv_30 field to ScreenedStock.

Purpose: These pure filter functions are the core logic of the screening pipeline. Each takes a ScreenedStock + config (and optionally external data), returns a FilterResult, and handles None/missing data gracefully. This plan creates the building blocks that Plan 02 will orchestrate.

Output: screener/pipeline.py with 10 filter functions + HV computation + stage runner helpers, updated ScreenedStock model, comprehensive tests.
- [x] **T02: 03-screening-pipeline 02** `est:4min`
  - Implement the scoring engine (SCOR-01, SCOR-02) and full pipeline orchestrator that ties together universe fetching, bar fetching, indicator computation, Stage 1/2 filtering, scoring, and sorting.

Purpose: Plan 01 created the individual filter functions and stage runners. This plan adds the scoring formula and the `run_pipeline()` function that orchestrates the entire 3-stage screening flow end-to-end, producing a complete list of scored and ranked ScreenedStock objects.

Output: Updated screener/pipeline.py with scoring + orchestration functions, updated tests/test_pipeline.py with scoring and pipeline tests.

## Files Likely Touched

- `models/screened_stock.py`
- `screener/pipeline.py`
- `tests/test_pipeline.py`
- `screener/pipeline.py`
- `tests/test_pipeline.py`
