# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 wires S01's pipeline internals to two user-visible surfaces: a `--top-n` CLI flag on `run-screener` and a "Perf 1M" column in the Rich results table. S01 is fully implemented on branch `gsd/M002/S01` (+934/-38 lines) and must be merged before S02 implementation — it provides `perf_1m: Optional[float]` on `ScreenedStock`, `compute_monthly_performance()` in `market_data.py`, and `run_pipeline(top_n=)` with the two-pass architecture. The current `gsd/M002/S02` branch has none of these changes.

Both CLI and display changes are purely additive and low-risk. The CLI flag follows the exact Typer `Annotated[type | None, typer.Option()]` pattern already used by the four existing options in `run_screener.py`. The display column follows the 13-column pattern in `render_results_table()`. One formatting nuance: TOPN-05 requires explicit sign on values (`-5.2%`, `+3.1%`), but the existing `fmt_pct()` produces `"3.1%"` for positives — a `fmt_pct_signed()` variant using `f"{value:+.1f}%"` is needed.

Verified: Typer 0.24.1 handles `int | None` with `min=1` correctly — `--top-n 0` produces a clean validation error, `--top-n 20` passes `20`, omission passes `None`. 345 tests currently pass on the S02 branch.

## Recommendation

1. **Merge S01 branch** — `git merge gsd/M002/S01` into `gsd/M002/S02`. The diff modifies `pipeline.py`, `market_data.py`, `screened_stock.py`, and adds `test_pipeline.py`/`test_market_data.py` tests. No overlap with S02's target files (`run_screener.py`, `display.py`). Should be conflict-free.
2. **Add `--top-n` CLI option** — `Annotated[int | None, typer.Option("--top-n", min=1, help="...")]` with default `None`. Pass through to `run_pipeline(top_n=top_n)` at line ~119 of `run_screener.py`.
3. **Add `fmt_pct_signed()` helper** — `f"{value:+.1f}%"` with `None` → `"N/A"`. Place next to `fmt_pct()` in `display.py`.
4. **Add "Perf 1M" column** — Insert between "HV%ile" and "Yield" in `render_results_table()`. Uses `fmt_pct_signed(stock.perf_1m)` for row values.
5. **Test both surfaces** — CLI: `CliRunner` + `@patch` stack asserting `top_n=20` reaches `run_pipeline`. Display: `Console(file=StringIO())` capture asserting column header and signed format. Follow existing patterns exactly.

## Requirements Owned by This Slice

| Requirement | Role | What S02 Must Deliver |
|-------------|------|-----------------------|
| TOPN-01 | primary | `--top-n N` CLI flag on `run-screener` that passes `top_n=N` to `run_pipeline()` |
| TOPN-05 | primary | "Perf 1M" column in Rich results table with signed percentage format (`-5.2%`, `+3.1%`) |
| TOPN-06 | primary | No flag = `top_n=None` = all stocks processed (backward compatible) |

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | `typer.Option` with `Annotated` pattern at `run_screener.py:55-73` | Four options already use this exact pattern |
| Table rendering | `rich.table.Table` `add_column` / `add_row` at `display.py:169-215` | 13 columns already defined — add 14th in same pattern |
| Number formatting | `fmt_pct()` at `display.py:107-118` | Handles `None → "N/A"` and `%.1f%`; extend with signed variant |
| CLI testing | `CliRunner` + `@patch` at `test_cli_screener.py:36-74` | 5 existing tests; clone pattern for `top_n` passthrough |
| Display testing | `Console(file=StringIO(), width=200)` at `test_options_chain.py:634-680` | `TestDisplayYieldColumn` is exact precedent for column-addition tests |
| Stock fixture | `_make_stock(**kwargs)` using `setattr` at `test_options_chain.py:50-54` | Already supports any field including `perf_1m` once it exists |

## Existing Code and Patterns

- **`scripts/run_screener.py:55-73`** — CLI option declarations. Pattern: `Annotated[type | None, typer.Option("--flag", help="...")]` with default. S02's `--top-n` is identical.
- **`scripts/run_screener.py:116-126`** — `run_pipeline()` call site. Currently passes 6 kwargs: `trade_client`, `stock_client`, `finnhub`, `cfg`, `on_progress`, `option_client`. S02 adds `top_n=top_n`.
- **`screener/display.py:169-193`** — 13 column definitions via `table.add_column()`. Order: `#, Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, HV%ile, Yield, Score, Sector`. S02 inserts "Perf 1M" after "HV%ile" at position 10 (before "Yield").
- **`screener/display.py:195-215`** — Row construction via `table.add_row()`. 13 values in positional order. S02 inserts `perf_1m_str` between `hv_pct_str` and `yield_str`.
- **`screener/display.py:107-118`** — `fmt_pct()`: `f"{value:.1f}%"` or `"N/A"`. No `+` sign for positives. S02 adds `fmt_pct_signed()` with `f"{value:+.1f}%"`.
- **`tests/test_cli_screener.py:36-74`** — `test_default_no_file_writes`: canonical CLI test — patches 8 deps, invokes via `CliRunner`, asserts `run_pipeline` was called. S02 clones this, asserting `top_n=20` in kwargs.
- **`tests/test_cli_screener.py:22-30`** — `test_screener_help`: asserts all option names appear in help output. Must add `--top-n` assertion.
- **`tests/test_display.py:205-212`** — `test_table_has_column_headers`: asserts column names in output. Must add `"Perf 1M"` to expected columns. Note: existing test does NOT check "HV%ile" or "Yield" — only a subset of columns are asserted.
- **`tests/test_display.py:30-57`** — `_make_stock()` helper: explicit params, no `perf_1m`. Set `stock.perf_1m = value` via `setattr` after creation (matches `test_options_chain.py` approach for `put_premium_yield`).
- **`tests/test_options_chain.py:634-680`** — `TestDisplayYieldColumn`: exact precedent for column-addition display tests. Creates stock with `put_premium_yield`, appends passing filter, renders to `StringIO`, asserts column header and formatted value.

## Constraints

- **S01 merge required first.** `perf_1m` field, `compute_monthly_performance()`, and `run_pipeline(top_n=)` are only on branch `gsd/M002/S01`. Current `gsd/M002/S02` branch has no `top_n` param on `run_pipeline()` and no `perf_1m` on `ScreenedStock`.
- **`top_n` type: `int | None`, default `None`.** Per D042, `None` = no cap (backward compatible, TOPN-06). Verified Typer 0.24.1 handles this natively.
- **`top_n` must be ≥ 1 when set.** `typer.Option(min=1)` produces clean validation error for `--top-n 0`. Verified.
- **Column alignment.** Both `add_column()` (position 10) and `add_row()` (value at position 10) must insert at the same index. Currently 13 columns → becomes 14. Mismatch causes silent misalignment of every column to the right.
- **Signed format for Perf 1M.** TOPN-05 specifies `-5.2%`, `+3.1%`. Python `f"{value:+.1f}%"` produces this. The existing `fmt_pct()` does NOT add `+` — must not reuse it.
- **345 existing tests must pass.** S02 changes are additive — no existing tests should break.

## Common Pitfalls

- **Column/row position mismatch** — `add_column("Perf 1M")` and the corresponding `add_row()` value must both be at index 10 (after `HV%ile`, before `Yield`). Off-by-one silently shifts every subsequent column.
- **Using `fmt_pct()` for Perf 1M** — `fmt_pct(3.1)` → `"3.1%"` (no `+`). Need `fmt_pct_signed()` for TOPN-05 compliance.
- **Not asserting `top_n` passthrough in CLI test** — CLI test must verify `run_pipeline` receives `top_n=20` when `--top-n 20` is passed. Check via `mock_pipeline.call_args.kwargs['top_n']`.
- **Forgetting `--top-n` in help test** — `test_screener_help` asserts all option names appear in help output. Add `--top-n` to assertions.
- **`_make_stock()` helper in `test_display.py` lacks `perf_1m` param** — Set `stock.perf_1m = value` after creation (simpler than extending helper; matches `test_options_chain.py` precedent).

## Open Risks

- **S01 merge conflicts** — Low probability. S01 modified `pipeline.py`, `market_data.py`, `screened_stock.py`, and test files. S02 targets `run_screener.py` and `display.py`. Only shared file is `models/screened_stock.py` which got a single field addition — no conflict expected.
- **`render_stage_summary` doesn't label top-N cap** — When `top_n` is active, Stage 1→Earnings count drop includes cap reduction but isn't labeled. Not in requirements (TOPN-05 only covers the results table). Acceptable to defer.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | N/A | Standard pattern already in codebase — no skill needed |
| Rich | N/A | Table pattern already established — no skill needed |
| Alpaca | N/A | No Alpaca API changes in S02 |

No skills to install — all technologies have well-established patterns in the codebase.

## Sources

- S01 branch diff (`git diff main..gsd/M002/S01`): 16 files, +934/-38 lines. Verified `perf_1m` field on `ScreenedStock`, `compute_monthly_performance()` in `market_data.py`, `run_pipeline(top_n=)` with two-pass sort/cap architecture, 5 `TestTopNPipelineCap` tests, 6 `TestComputeMonthlyPerformance` tests.
- `scripts/run_screener.py` — CLI option patterns and `run_pipeline()` call site (lines 55-126)
- `screener/display.py` — Column definitions, row construction, formatter helpers (lines 107-215)
- `tests/test_cli_screener.py` — 5 CLI tests using `CliRunner` + `@patch` stack pattern
- `tests/test_display.py` — 17+ display tests with `_make_stock()` helper and `Console(file=StringIO())` capture (487 lines)
- `tests/test_options_chain.py:634-680` — `TestDisplayYieldColumn` as exact precedent for column-addition display tests
- Typer 0.24.1 — Verified `int | None` with `min=1` works correctly (None default, int passthrough, min validation)
- 345 tests collected and passing on current `gsd/M002/S02` branch
