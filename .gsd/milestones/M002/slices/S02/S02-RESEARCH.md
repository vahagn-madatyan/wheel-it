# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 wires the S01 pipeline internals to user-visible surfaces: a `--top-n` CLI flag on `run-screener` and a "Perf 1M" column in the Rich results table. The S01 code lives on branch `gsd/M002/S01` and must be merged before S02 implementation — it provides `perf_1m` on `ScreenedStock`, `compute_monthly_performance()` in `market_data.py`, and `run_pipeline(top_n=)` with two-pass architecture. The current `gsd/M002/S02` branch has none of these changes.

Both CLI and display changes are purely additive. The CLI flag follows the exact pattern of the existing four Typer options in `run_screener.py`. The display column follows the pattern of the 13 existing columns in `render_results_table()`. One formatting nuance: TOPN-05 requires explicit sign on values (`-5.2%`, `+3.1%`), but the existing `fmt_pct()` produces `"3.1%"` for positives — a signed variant using `f"{value:+.1f}%"` is needed.

## Recommendation

1. **Merge S01 branch** — `git merge gsd/M002/S01` into `gsd/M002/S02`. The diff is +934/-38 lines across `pipeline.py`, `market_data.py`, `screened_stock.py`, and test files. No overlap with S02's target files (`run_screener.py`, `display.py`). This should be conflict-free.
2. **Add `--top-n` CLI option** — `Annotated[int | None, typer.Option("--top-n", min=1, help="...")]` with default `None`. Pass through to `run_pipeline(top_n=top_n)`. Typer 0.24.1 handles `int | None` with `min=1` correctly.
3. **Add "Perf 1M" column** — Insert between "HV%ile" and "Yield" in `render_results_table()`. Add a `fmt_pct_signed()` helper: `f"{value:+.1f}%"` with None → "N/A".
4. **Test both surfaces** — CLI: `CliRunner` + `@patch` stack asserting `top_n=20` reaches `run_pipeline`. Display: `Console(file=StringIO())` capture asserting column header and formatted value. Follow existing `test_cli_screener.py` and `test_options_chain.py:TestDisplayYieldColumn` patterns.

## Requirements Owned by This Slice

| Requirement | Role | What S02 Must Deliver |
|-------------|------|-----------------------|
| TOPN-01 | primary | `--top-n N` CLI flag on `run-screener` that passes `top_n=N` to `run_pipeline()` |
| TOPN-05 | primary | "Perf 1M" column in Rich results table with signed percentage format (`-5.2%`, `+3.1%`) |
| TOPN-06 | primary | No flag = `top_n=None` = all stocks processed (backward compatible) |

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | `typer.Option` with `Annotated` | Already used for `--verbose`, `--preset`, `--config`, `--update-symbols` |
| Table rendering | `rich.table.Table` `add_column` / `add_row` | 13 columns already in `render_results_table()` |
| Number formatting | `fmt_pct()` in `screener/display.py` | Handles `None → "N/A"` and `%.1f%`; extend with signed variant |
| CLI testing | `typer.testing.CliRunner` + `@patch` | 5 existing CLI tests in `test_cli_screener.py` |
| Display testing | `Console(file=StringIO(), width=200)` capture | Pattern in `test_options_chain.py:TestDisplayYieldColumn` |

## Existing Code and Patterns

- `scripts/run_screener.py:55-73` — CLI option pattern: `Annotated[type | None, typer.Option("--flag", help="...")]` with default. S02's `--top-n` follows this exactly.
- `scripts/run_screener.py:119-126` — `run_pipeline()` call site. S02 adds `top_n=top_n` kwarg. Currently passes 6 args: `trade_client`, `stock_client`, `finnhub`, `cfg`, `on_progress`, `option_client`.
- `screener/display.py:169-193` — Column definitions. 13 columns: `#, Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, HV%ile, Yield, Score, Sector`. S02 inserts "Perf 1M" after "HV%ile" (position 10, before "Yield").
- `screener/display.py:195-215` — Row construction via `add_row()`. S02 adds `perf_1m` formatted value between `hv_pct_str` and `yield_str`.
- `screener/display.py:107-118` — `fmt_pct()`: `f"{value:.1f}%"` or `"N/A"`. No `+` sign for positives. S02 adds `fmt_pct_signed()` using `f"{value:+.1f}%"`.
- `tests/test_cli_screener.py:36-74` — `test_default_no_file_writes`: canonical CLI test — patches 8 deps, invokes via `CliRunner`, asserts `run_pipeline` was called. S02 clones this, asserting `top_n=20` in kwargs.
- `tests/test_cli_screener.py:22-30` — `test_screener_help`: asserts all option names in help output. Must add `--top-n` assertion.
- `tests/test_display.py:30-57` — `_make_stock()` helper: creates `ScreenedStock` with keyword fields. Does NOT accept `perf_1m` — set `stock.perf_1m = value` after creation (matching `test_options_chain.py` approach where `put_premium_yield` is set via `setattr`).
- `tests/test_options_chain.py:634-680` — `TestDisplayYieldColumn`: exact pattern for column-addition display tests. Creates stock, appends filter result, renders to `StringIO`, asserts column header and value in output.

## Constraints

- **S01 merge required first.** `perf_1m` field, `compute_monthly_performance()`, and `run_pipeline(top_n=)` are only on branch `gsd/M002/S01`. Current S02 branch `pipeline.py` has no `top_n` param; `screened_stock.py` has no `perf_1m` field.
- **`top_n` type: `int | None`, default `None`.** Per D042, `None` = no cap (backward compatible, TOPN-06). Typer 0.24.1 handles this natively.
- **`top_n` must be ≥ 1 when set.** `typer.Option(min=1)` produces validation error for `--top-n 0`.
- **Column alignment: "Perf 1M" between "HV%ile" and "Yield".** Both `add_column()` and `add_row()` must insert at the same position. Currently 13 columns → becomes 14. Mismatch causes silent misalignment.
- **Signed format for Perf 1M.** TOPN-05 specifies `-5.2%`, `+3.1%`. Python `f"{value:+.1f}%"` produces this.
- **345 existing tests must pass.** S02 changes are additive.

## Common Pitfalls

- **Column/row position mismatch** — `add_column("Perf 1M")` at one index but `add_row()` value at a different index silently misaligns every column to its right. Count carefully: both at position 10 (after HV%ile, before Yield).
- **Using `fmt_pct()` for Perf 1M** — `fmt_pct(3.1)` → `"3.1%"` (no `+`). Need `fmt_pct_signed()` for TOPN-05 compliance.
- **Not asserting `top_n` passthrough** — CLI test must verify `run_pipeline` receives `top_n=20` when `--top-n 20` is passed. Check `mock_pipeline.call_args.kwargs['top_n']`.
- **Forgetting `--top-n` in help test** — `test_screener_help` asserts all option names appear in help output. Add `--top-n` assertion or coverage gap.
- **`_make_stock()` helper in `test_display.py` lacks `perf_1m` param** — Set `stock.perf_1m = value` after creation (simpler than extending helper; matches `test_options_chain.py` precedent with `setattr`).

## Open Risks

- **S01 merge conflicts** — Low probability. S01 modified `pipeline.py`, `market_data.py`, `screened_stock.py`, and test files. S02 targets only `run_screener.py` and `display.py`. Only risk: if pipeline.py import line diverged, but both branches show same base.
- **`render_stage_summary` doesn't show top-N cap** — When `top_n` active, the count drops between Stage 1 and Earnings due to cap, but summary panel doesn't label this. Not in requirements — acceptable to defer.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | N/A | Standard pattern already in codebase — no skill needed |
| Rich | N/A | Table pattern already established — no skill needed |
| Alpaca | N/A | No Alpaca API changes in S02 |

No skills to install — all technologies have well-established patterns in the codebase.

## Sources

- S01 branch diff (`git diff main..gsd/M002/S01`): 16 files, +934/-38 lines. Confirmed `perf_1m` field, `compute_monthly_performance()`, `run_pipeline(top_n=)`, two-pass architecture, and new pipeline tests.
- `scripts/run_screener.py` — CLI option patterns and `run_pipeline()` call site (lines 55-126)
- `screener/display.py` — column definitions, row construction, formatter helpers (lines 107-215)
- `tests/test_cli_screener.py` — 5 CLI tests using `CliRunner` + `@patch` stack pattern
- `tests/test_display.py` — 17 display tests with `_make_stock()` helper and `Console(file=StringIO())` capture
- `tests/test_options_chain.py:634-680` — `TestDisplayYieldColumn` as precedent for column-addition display tests
- Typer 0.24.1 installed — `int | None` with `min=1` works correctly
- 345 tests collected and passing on current `gsd/M002/S02` branch
