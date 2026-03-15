# S01: Put Screener — Research

**Date:** 2026-03-12

## Summary

The `screen_puts()` function mirrors `screen_calls()` from `screener/call_screener.py` (315 lines) — same filter pipeline, same Alpaca SDK calls, same dataclass-based output. The key structural difference: put screener handles **multiple symbols** (like the old `sell_puts()` path), while call screener handles one symbol at a time. The old put path in `core/strategy.py` + `core/execution.py` uses a custom scoring formula, no spread filter, DTE 0–21 days, and mixes screening with execution. All of this gets replaced by a clean screening-only function with annualized return scoring, spread filter, and DTE 14–60.

The annualized return formula already exists in `screener/pipeline.py` as `compute_put_premium_yield()` — identical math: `(bid / strike) * (365 / dte) * 100`. The put screener will define its own `compute_put_annualized_return()` following the call screener's naming convention rather than importing from pipeline (keeps the module self-contained, same pattern as call screener).

The biggest design question is multi-symbol API handling. The old path batches all symbols into one `get_options_contracts()` call. The call screener sends one symbol. For puts, the multi-symbol batch approach is more efficient (one API call vs N), and the old path already has pagination for large contract sets. The new `screen_puts()` should use the batch approach but call `trade_client.get_option_contracts()` directly (matching call screener's direct SDK usage) rather than going through `BrokerClient.get_options_contracts()`.

## Recommendation

Build `screener/put_screener.py` as a structural mirror of `call_screener.py` with these differences:

1. **Multi-symbol input** — accepts `list[str]` of symbols + `buying_power` float
2. **Buying power pre-filter** — fetch latest trade prices, discard symbols where `100 * price > buying_power`
3. **One-per-underlying** — after scoring, keep only the best contract per underlying symbol (diversification rule from old path)
4. **PUT contracts** — `ContractType.PUT` instead of `ContractType.CALL`
5. **Annualized return** — `(bid / strike) * (365 / dte) * 100` (strike replaces cost_basis since strike is the cash-secured amount)

Test file follows `test_call_screener.py` (969 lines) structure: math tests, filter tests, ranking tests, error handling, dataclass tests, multi-symbol tests, preset tests.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Annualized return math | `compute_put_premium_yield()` in `pipeline.py` | Same formula — but don't import it; define `compute_put_annualized_return()` locally (matches call screener pattern, keeps module self-contained) |
| OI/spread thresholds | `ScreenerConfig.options` (Pydantic model) | Already preset-configurable; D037 established this pattern for call screener |
| Delta thresholds | `config/params.py` `DELTA_MIN`/`DELTA_MAX` | Same import pattern as call screener |
| Mock helpers | `test_call_screener.py` `_make_mock_contract`, `_make_mock_snapshot`, `_mock_clients` | Copy and adapt — they build the exact mock structures needed |
| Snapshot batching | `call_screener.py` lines 159–165 | 100-per-batch pattern with `OptionSnapshotRequest` |

## Existing Code and Patterns

- `screener/call_screener.py` — **Primary template.** 315 lines. `screen_calls()` does: fetch contracts → filter strike ≥ cost_basis → OI pre-filter → batch snapshots → spread/delta filter → compute return → sort. Mirror this pipeline for puts, swapping cost_basis filter for buying-power pre-filter and one-per-underlying selection.
- `core/strategy.py` — **Being replaced.** 55 lines. `filter_options()` uses YIELD_MIN/YIELD_MAX (not used in new path), requires non-None delta (new path passes None-delta contracts per D039), no spread filter. `score_options()` uses custom formula `(1 - |delta|) * (250 / (DTE + 5)) * (bid / strike)` — replaced by annualized return.
- `core/execution.py` — **Being replaced (S02).** `sell_puts()` (34 lines) mixes screening + order execution. Uses `BrokerClient` wrapper methods. `sell_calls()` is dead code (replaced by `screen_calls` in M001/S10).
- `models/contract.py` — **Not needed.** The `Contract` dataclass was the bridge between old SDK types and `strategy.py` functions. `screen_puts()` works directly with Alpaca SDK objects + snapshots (same as call screener). `PutRecommendation` replaces `Contract` for the screener output.
- `config/params.py` — `DELTA_MIN=0.15`, `DELTA_MAX=0.30` (imported by both screeners). `EXPIRATION_MIN=0`, `EXPIRATION_MAX=21` (old values, NOT used by new put screener — DTE range hardcoded as module constants per D032). `YIELD_MIN`/`YIELD_MAX`/`SCORE_MIN`/`OPEN_INTEREST_MIN` become dead with `screen_puts()` (used only by old `strategy.py`).
- `tests/test_call_screener.py` — **Test template.** 969 lines, comprehensive. Sections: annualized return math, dataclass, screen_calls filtering, DTE range, Rich table, CLI, strategy integration, preset thresholds, snapshot batching. Follow this structure.
- `scripts/run_strategy.py` — **Consumer (S02).** Currently imports `sell_puts` from `core/execution` (line 25) and calls it at line 212. S01 does NOT touch this file — S02 will wire `screen_puts()` in.

## Constraints

- `screen_puts()` must use `trade_client` (TradingClient) and `option_client` (OptionHistoricalDataClient) directly — same as call screener. NOT the `BrokerClient` wrapper (which couples DTE range to `config/params.py` values).
- DTE range: `_PUT_DTE_MIN = 14`, `_PUT_DTE_MAX = 60` — matching call screener per D032. This is a change from old path's 0–21 day range.
- Delta filter: `abs(delta)` between `DELTA_MIN` and `DELTA_MAX` from `config/params.py`. None-delta contracts pass (D039).
- OI threshold from `ScreenerConfig.options.options_oi_min`. Spread threshold from `ScreenerConfig.options.options_spread_max`. These are preset-configurable.
- Spread formula: `(ask - bid) / midpoint` where `midpoint = (bid + ask) / 2` (D034).
- Must not break 368 existing tests.
- No execution logic in `screen_puts()` — pure screening, returns `list[PutRecommendation]`.
- Buying power parameter is in the boundary map signature: `screen_puts(trade_client, option_client, symbols, buying_power, config?)`.

## Common Pitfalls

- **Multi-symbol contract fetch needs pagination** — Alpaca limits to 1000 contracts per page. The old `BrokerClient.get_options_contracts()` handles pagination. `screen_puts()` must implement its own pagination loop since it uses `trade_client` directly (same as old path lines 80–89 in `broker_client.py`). The call screener skips pagination because single-symbol rarely exceeds 1000 contracts.
- **Buying power pre-filter requires a separate API call** — `get_stock_latest_trade()` is needed to get current prices before filtering by affordability. This is an extra call the call screener doesn't make. Handle the API failure gracefully (exclude symbol, don't crash).
- **One-per-underlying must happen after scoring** — The old `select_options()` picks the best-scoring contract per underlying. Do this after annualized return computation, not before. Selecting before scoring could discard the best contract.
- **Snapshot batching limit is 100** — Alpaca OptionSnapshotRequest allows up to 100 symbols per batch. Multiple symbols × multiple contracts could mean many batches. Pre-filter by OI before snapshot fetch to minimize API calls (same pattern as call screener).
- **DTE range change is invisible but significant** — Old path: 0–21 days. New path: 14–60 days. This completely changes which contracts are available. The overlap is only 14–21 days. This is intentional (gamma risk avoidance, better time value) but worth noting in the summary.

## Open Risks

- **Multi-symbol API call may be slow** — Fetching contracts for 20+ symbols in one request, then snapshots for all passing contracts, could be slow. Old path had the same pattern and it worked, but snapshot batching could take several seconds. Not a blocker, but `screen_puts()` should log timing.
- **Buying power filter may exclude all symbols** — If buying power is very low (e.g., $5000) and all symbols have prices above $50, every symbol fails the pre-filter. `screen_puts()` returns empty list. This is correct behavior but could be surprising. Should log clearly.
- **EXEC-01 through EXEC-09 requirements are referenced in the roadmap but not defined in REQUIREMENTS.md** — These need to be created during planning. The research shows no Active requirements to own; the requirements will be defined as part of S01 planning.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Alpaca Trading API | `lacymorrow/openclaw-alpaca-trading-skill@alpaca-trading` (31 installs) | available — low install count, existing patterns in codebase are sufficient |
| Options strategy | `tradermonty/claude-trading-skills@options-strategy-advisor` (169 installs) | available — advisory skill, not needed for implementation |

No skill installation recommended — the codebase already has comprehensive working patterns in `call_screener.py` and `test_call_screener.py`.

## Sources

- `screener/call_screener.py` — primary template (315 lines, screen_calls + CallRecommendation + compute_call_annualized_return)
- `core/strategy.py` — old scoring formula being replaced (55 lines)
- `core/execution.py` — old sell_puts mixing screening + execution (63 lines)
- `screener/pipeline.py:773-792` — existing `compute_put_premium_yield()` confirms formula
- `tests/test_call_screener.py` — test template (969 lines, comprehensive coverage)
- `config/params.py` — delta range, old DTE range, old scoring params
- `screener/config_loader.py` — `ScreenerConfig` / `OptionsConfig` models for OI/spread thresholds
