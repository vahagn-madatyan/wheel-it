# T02: 03-screening-pipeline 02

**Slice:** S03 — **Milestone:** M001

## Description

Implement the scoring engine (SCOR-01, SCOR-02) and full pipeline orchestrator that ties together universe fetching, bar fetching, indicator computation, Stage 1/2 filtering, scoring, and sorting.

Purpose: Plan 01 created the individual filter functions and stage runners. This plan adds the scoring formula and the `run_pipeline()` function that orchestrates the entire 3-stage screening flow end-to-end, producing a complete list of scored and ranked ScreenedStock objects.

Output: Updated screener/pipeline.py with scoring + orchestration functions, updated tests/test_pipeline.py with scoring and pipeline tests.

## Must-Haves

- [ ] "Each surviving stock has a wheel-suitability score (0-100) based on three weighted components: capital efficiency, volatility proxy, fundamental strength"
- [ ] "Capital efficiency is weighted highest in the scoring formula"
- [ ] "Stocks with None HV get a neutral volatility score (0.5) instead of being eliminated"
- [ ] "Results are returned sorted by score descending"
- [ ] "The pipeline fetches the full Alpaca-tradable universe via get_all_assets"
- [ ] "Existing symbol_list.txt symbols are merged into the universe"
- [ ] "Optionable symbols are identified via a single bulk GetAssetsRequest(attributes='options_enabled') call"
- [ ] "Bars are batch-fetched and indicators computed for the entire universe before filtering"
- [ ] "Stage 1 (cheap Alpaca filters) runs before Stage 2 (expensive Finnhub filters)"
- [ ] "Stocks with no bar data get a FilterResult recording 'No bar data' and skip subsequent stages"
- [ ] "ALL ScreenedStock objects (passing and eliminated) are returned with FilterResults populated"

## Files

- `screener/pipeline.py`
- `tests/test_pipeline.py`
