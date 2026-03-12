# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 adds two thin layers on top of S01's pipeline work: a `--top-n N` Typer CLI option on `run-screener` that passes through to `run_pipeline(top_n=N)`, and a "Perf 1M" column in the Rich results table reading `ScreenedStock.perf_1m`. Both are straightforward — the CLI follows the existing `--verbose`/`--preset`/`--update-symbols` Typer pattern exactly, and the display column follows the HV%ile/Yield column pattern already established.

**Critical dependency issue:** S01's code lives on the `gsd/M002/S01` branch and has NOT been merged into main or the current `gsd/M002/S02` branch. The three artifacts S02 consumes — `run_pipeline(top_n=)` parameter, `ScreenedStock.perf_1m` field, and `compute_monthly_performance()` — do not exist on the current branch. S01 must be merged before S02 tasks can execute.

## Recommendation

Merge S01 branch into the S02 branch first, then implement two small tasks: (1) `--top-n` CLI flag + passthrough + tests, (2) "Perf 1M" display column + tests. Both are low-risk, mechanically follow established patterns, and require no new libraries or external research.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | Typer `Annotated[int \| None, typer.Option(...)]` | Already used for `--verbose`, `--preset`, `--config`, `--update-symbols` |
| Rich table columns | `table.add_column()` + `fmt_pct()` | Exact pattern used for HV%ile and Yield columns |
| CLI testing | `typer.testing.CliRunner` + `unittest.mock.patch` | Established in `test_cli_screener.py` with 4 existing tests |
| Display testing | `Console(file=StringIO(), width=200)` capture | Pattern in `test_options_chain.py:test_yield_column_in_results_table` |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — CLI entry point. Uses `Annotated[type, typer.Option(...)]` for all flags. Add `top_n` parameter here with same pattern. Pass it to `run_pipeline(..., top_n=top_n)`.
- `screener/display.py:render_results_table()` — Results table. Columns added via `table.add_column()` + corresponding `table.add_row()` value. `fmt_pct()` already handles `None → "N/A"` and formats as `X.X%`. Insert "Perf 1M" column after "HV%ile" (before "Yield").
- `screener/display.py:fmt_pct()` — Formats `float | None` as `"X.X%"` or `"N/A"`. Handles positive and negative values. Reuse directly for perf_1m display — output like `-5.2%` or `+3.1%` (but note: `fmt_pct` does NOT add a `+` sign for positives; decide whether to add one or use as-is).
- `tests/test_cli_screener.py` — 4 existing CLI tests using `CliRunner` + heavy mocking. Pattern: patch `run_pipeline`, `create_broker_client`, `require_finnhub_key`, `FinnhubClient`, `progress_context`, `render_*` functions. Add a test that passes `--top-n 20` and asserts `run_pipeline` receives `top_n=20`.
- `tests/test_options_chain.py:test_yield_column_in_results_table` — Display column test pattern: create a `ScreenedStock` with the field set, render to a `StringIO` console, assert column header and formatted value appear in output. Follow this exactly for "Perf 1M".
- `models/screened_stock.py:ScreenedStock` — S01 adds `perf_1m: Optional[float] = None` after `hv_percentile`. S02 only reads this field.

## Constraints

- S01 branch (`gsd/M002/S01`) must be merged into `gsd/M002/S02` before any S02 code can work — `run_pipeline` currently lacks `top_n` parameter and `ScreenedStock` lacks `perf_1m` field.
- `top_n` must be `int | None` (not `int`) — `None` means no cap (TOPN-06 backward compatibility).
- Typer maps `--top-n` to Python parameter `top_n` automatically (hyphen → underscore).
- `perf_1m` is a percentage value (e.g. `-5.2` for 5.2% decline) — `fmt_pct` will render it as `-5.2%`.
- D019: Module-level imports in CLI entry points for patchability — already followed in `run_screener.py`.
- D015: Console parameter injection for testability — `render_results_table` already accepts `console` parameter.

## Common Pitfalls

- **`fmt_pct` doesn't add `+` sign for positives** — `fmt_pct(3.1)` returns `"3.1%"` not `"+3.1%"`. The roadmap says "Formatted as percentage with sign (e.g. -5.2%, +3.1%)". Either modify `fmt_pct` (risky — used elsewhere) or use a dedicated `fmt_signed_pct` helper for perf_1m.
- **Column ordering in `add_row` must match `add_column`** — When inserting "Perf 1M" column, the corresponding value must be inserted at the same position in the `add_row()` call. Off-by-one here silently shifts all subsequent columns.
- **Typer Option type for optional int** — Use `Annotated[int | None, typer.Option("--top-n", ...)] = None`. Typer handles `int | None` correctly — omitted flag → `None`, provided flag → parsed int.
- **Negative top_n values** — Should validate that `top_n` is positive when provided. Typer has `min=1` via callback or `typer.Option(min=1)`. Or validate in the `run()` function body.
- **Existing test mock stacks are deep** — `test_default_no_file_writes` patches 8 functions. Adding `top_n` passthrough test requires the same mock stack. Extract a helper or keep the pattern consistent.

## Open Risks

- **S01 merge conflicts** — The S01 branch modified `screener/pipeline.py` significantly (two-pass architecture), `models/screened_stock.py`, `screener/market_data.py`, and `tests/`. Merging into S02's branch (which diverged from the same base) may produce conflicts, particularly in `pipeline.py`. Risk is low since S02 branch has no production code changes, only `.gsd/` artifacts.
- **Placeholder S01 summary** — S01's summary was doctor-created placeholder. Should verify S01's actual task summaries and test results before treating S01 as complete. The code on the S01 branch looks correct from inspection.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer (CLI framework) | — | none found (no skill needed — trivial usage) |
| Rich (terminal display) | — | none found (no skill needed — trivial usage) |

## Sources

- `scripts/run_screener.py` — existing CLI flag pattern (Annotated + typer.Option)
- `screener/display.py` — existing column pattern (add_column + fmt_pct + add_row)
- `tests/test_cli_screener.py` — existing CLI test pattern (CliRunner + mock stack)
- `tests/test_options_chain.py:637-681` — existing display column test pattern (StringIO console capture)
- `gsd/M002/S01` branch — S01 implementation (perf_1m field, compute_monthly_performance, run_pipeline top_n parameter, two-pass pipeline architecture)
