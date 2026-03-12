# S07: Pipeline Fix + Preset Overhaul — Research

**Date:** 2026-03-11

## Summary

S07 owns 8 requirements (FIX-01..04, PRES-01..04) that together fix the zero-results pipeline bug and overhaul presets so the screener produces meaningful, differentiated output across conservative/moderate/aggressive profiles.

The root causes of zero results are three independent killers acting in concert: (1) `avg_volume_min` is 2,000,000 in all three presets — this alone eliminates ~95% of the universe since only mega-cap stocks clear 2M shares/day; (2) every filter function returns `passed=False` when a metric is `None`, meaning any stock missing even one Finnhub data point is eliminated; (3) Finnhub's `totalDebtToEquity` returns percentage values (e.g., 150.0 for 150% D/E) while the threshold is set as a ratio (`debt_equity_max: 1.0`), so even conservatively-leveraged companies fail. All three must be fixed for results to appear.

**Critical prerequisite:** The screener code (S01–S06) lives entirely in the `scanning-improvements` branch (106 commits ahead) and is NOT on the current working branch `gsd/M001/S07`. The `.py` source files were deleted from disk but `.pyc` caches remain. Before any S07 implementation, the `scanning-improvements` branch must be merged into the working branch. This is a merge, not new code — treat it as a prerequisite step, not a task.

## Recommendation

**Approach: Fix in layers — merge first, then None-tolerance, then D/E normalization, then preset overhaul, then differentiation verification.**

1. **Merge `scanning-improvements` into `gsd/M001/S07`** to restore all S01–S06 source files, tests (63 test functions across 10 test files), preset YAMLs, and pyproject.toml changes.
2. **Fix None-handling in filter functions** — Change all 10 filter functions to return `passed=True` when the metric is `None`, with a reason like `"No data — passing with neutral score"`. This requires updating ~10 corresponding test assertions from `passed is False` to `passed is True`.
3. **Normalize Finnhub D/E values** — Add percentage-to-ratio conversion in `run_stage_2_filters()` after `extract_metric()` call, consistent with D009 (conversion at boundary). Check if value > 10 → divide by 100. Keep filter functions pure.
4. **Overhaul preset YAMLs** — Differentiate ALL categories (fundamentals, technicals, options, sectors) across all three presets. Add `sector_avoid`/`sector_prefer` support (map to existing `sectors.exclude`/`sectors.include` in config model).
5. **Verification** — Run `run-screener --preset moderate` against live data and confirm ≥1 result.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Config validation | Pydantic `ScreenerConfig` model in `config_loader.py` | Already validates all thresholds with field_validators; extend, don't replace |
| Metric extraction | `extract_metric()` with `METRIC_FALLBACK_CHAINS` in `finnhub_client.py` | Handles Finnhub key name variations; add normalization after, not inside |
| Filter result pattern | `FilterResult` dataclass in `models/screened_stock.py` | D008 — pure filter functions return FilterResult, never raise |
| Deep merge | `deep_merge()` in `config_loader.py` | Already handles nested YAML override of preset values |

## Existing Code and Patterns

- `screener/pipeline.py` (860 lines, in `scanning-improvements`) — All 10 filter functions, `run_stage_1_filters`, `run_stage_2_filters`, `compute_wheel_score`, `run_pipeline`. Every filter returns `passed=False` on None — this is the primary code to change for FIX-03.
- `screener/pipeline.py:run_stage_2_filters()` — Populates `stock.debt_equity` via `extract_metric(metrics, "debt_equity")` with no normalization. This is where D/E percentage→ratio conversion belongs (FIX-02, per D009 boundary conversion pattern).
- `screener/finnhub_client.py:extract_metric()` — Walks `METRIC_FALLBACK_CHAINS["debt_equity"]` through keys `totalDebtToEquity`, `totalDebtToEquityQuarterly`, `totalDebtToEquityAnnual`. Returns raw float — no normalization. Leave this pure; normalize in `run_stage_2_filters`.
- `screener/config_loader.py` — `ScreenerConfig` Pydantic model with `FundamentalsConfig`, `TechnicalsConfig`, `OptionsConfig`, `SectorsConfig`. The `SectorsConfig` already has `include`/`exclude` lists that can serve as `sector_prefer`/`sector_avoid`. No model changes needed for PRES-04 — just populate the YAML files.
- `config/presets/*.yaml` (in `scanning-improvements`) — Currently all three share **identical** technicals (`price_min: 10`, `price_max: 50`, `avg_volume_min: 2000000`, `rsi_max: 60`, `above_sma200: true`) and identical empty sector lists. Only fundamentals differ. This is the primary data to change for PRES-01..04 and FIX-04.
- `screener/display.py` — Rich table output, filter breakdown. No changes needed for S07 (display already handles the data shape).
- `tests/test_pipeline.py` (63 test functions) — Every `test_*_none_fails` test asserts `passed is False` and `"unavailable" in reason`. All of these must be updated to assert `passed is True` with new neutral-pass reason text for FIX-03.
- `models/screened_stock.py` — `ScreenedStock.passed_all_filters` property checks `all(r.passed for r in self.filter_results)`. After FIX-03, None-metric stocks will pass individual filters, so they survive to scoring where `compute_wheel_score` already handles None with 0.5 neutral score (D013).

## Constraints

- **Branch merge required first** — 106 commits in `scanning-improvements` must be merged into `gsd/M001/S07` before any S07 code changes. Source files are missing from disk. Without this, there is literally nothing to edit.
- **D008: Filter function purity** — Filters take `ScreenedStock + config → FilterResult`, never raise, never call APIs. D/E normalization must happen in `run_stage_2_filters`, not in `filter_debt_equity`.
- **D009: Single unit system** — Conversion at boundary. Finnhub percentage→ratio conversion happens once in `run_stage_2_filters`, all downstream code sees ratio values.
- **D013: None handling in scoring** — `compute_wheel_score` already gives 0.5 neutral score to None HV and None fundamentals. FIX-03 must ensure stocks reach scoring by not failing at filter stage.
- **Pydantic validator: `debt_equity_max` ≤ 10** — The existing validator rejects values > 10 as "unusually high". This is correct for ratio format but would break if someone tried to set percentage thresholds. Keep ratio format in config, normalize Finnhub data to match.
- **Test count stability** — 63 existing test functions must continue passing. None-handling tests need assertion direction changed, not deleted.
- **`config/presets/` directory must exist** — Currently only in `scanning-improvements` branch. Merge creates it.

## Common Pitfalls

- **Changing `extract_metric` instead of `run_stage_2_filters`** — Tempting to normalize inside the extraction function, but this breaks purity (D008) and makes the fix invisible to callers. Normalize in the stage runner where the boundary conversion belongs (D009).
- **Treating all None-metric filters identically** — Stage 1 filters (price, volume) measure Alpaca data availability. A stock with `price=None` genuinely has no bar data and should still fail — it can't be screened. Stage 2 filters (Finnhub fundamentals) should tolerate None because Finnhub coverage is patchy. The split: Stage 1 None = fail (no data to screen), Stage 2 None = pass with neutral (Finnhub gap, not stock fault).
- **Forgetting `above_sma200=None`** — SMA200 filter already has a disabled path (`config.technicals.above_sma200 = false`). For aggressive preset, set this to `false` rather than tolerating None, keeping the filter logic clean.
- **D/E normalization guard** — Not all Finnhub D/E values are percentages. Some may already be ratios (< 10). Use a heuristic: if `debt_equity > 10`, divide by 100. This handles both formats. Log a debug message when conversion triggers.
- **Empty sector lists still match** — `filter_sector` with empty `include` list passes all sectors. For PRES-04, conservative should use `exclude` list (avoid risky sectors), not `include` list (which would require listing every allowed sector).
- **YAML integer underscores** — D002 prohibits underscore separators in YAML integers. Write `500000` not `500_000` in preset files. Python code can use underscores, but YAML values must not.

## Open Risks

- **Finnhub D/E format uncertainty** — Without a live API call, the percentage-vs-ratio question is inferred from the bug behavior and common Finnhub reports. The heuristic (> 10 → divide by 100) is robust but should be verified with a diagnostic script during implementation. If Finnhub uses yet another format, the guard needs adjustment.
- **Merge conflicts** — `gsd/M001/S07` has 1 commit not in `scanning-improvements` (the M001 roadmap docs). `scanning-improvements` has 106 commits not in current branch. Merge should be clean since they touch different files (docs vs screener code), but `pyproject.toml` and `.gitignore` could conflict.
- **Volume threshold sensitivity** — Dropping `avg_volume_min` from 2M to 500K (moderate) or 200K (aggressive) significantly expands the universe. More stocks means more Finnhub API calls per run, which may hit the 60 calls/min rate limit during Stage 2. The existing 1.1s throttle handles this, but run time will increase proportionally.
- **Preset differentiation judgment calls** — The roadmap specifies `avg_volume_min` values (conservative=1M, moderate=500K, aggressive=200K) but doesn't specify exact values for `price_max`, `rsi_max`, `above_sma200`, or sector lists. These must be chosen during implementation using reasonable financial judgment.
- **Test assertion flip count** — Changing None-handling from fail to pass touches ~8-10 test functions. Each must be individually verified to not mask real filter bugs.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Finnhub API | `adaptationio/skrillz@finnhub-api` (249 installs) | available — not installed |
| Alpaca Trading | `lacymorrow/openclaw-alpaca-trading-skill@alpaca-trading` (20 installs) | available — not installed |
| Pydantic | none found | N/A — well-understood, no skill needed |
| Rich | none found | N/A — already implemented in S04 |

Neither skill is critical for S07. The Finnhub skill (249 installs) could help verify D/E data format if the heuristic proves insufficient, but the core work is Python refactoring, not API integration.

## Sources

- Finnhub D/E data format — inferred from `METRIC_FALLBACK_CHAINS` key names (`totalDebtToEquity`) and filter behavior (source: `screener/finnhub_client.py` in `scanning-improvements` branch)
- Filter None-handling pattern — all 10 filters return `passed=False` on None (source: `screener/pipeline.py` lines 56-282 in `scanning-improvements`)
- Existing test assertions — 63 test functions with explicit None-fails assertions (source: `tests/test_pipeline.py` in `scanning-improvements`)
- Preset YAML analysis — all three presets share identical technicals section (source: `config/presets/*.yaml` in `scanning-improvements`)
- Branch divergence — 106 commits in `scanning-improvements` vs 1 unique commit in `gsd/M001/S07`, merge base at `ed09d4e` (source: `git log --oneline scanning-improvements ^gsd/M001/S07`)
