# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is a low-risk, thin integration slice that wires S01's pipeline changes (`top_n` parameter, `perf_1m` field) into the user-facing CLI and display layer. Three requirements are owned here: TOPN-01 (CLI flag), TOPN-05 (Perf 1M column), and TOPN-06 (backward compatibility when flag omitted). All three are straightforward — the CLI flag is a one-line Typer option, the display column follows existing patterns (HV%ile, Yield), and backward compatibility is inherent in `top_n=None` passthrough.

**Critical dependency:** S01 has not been implemented yet. The `perf_1m` field on `ScreenedStock` and the `top_n` parameter on `run_pipeline()` do not exist in the codebase. S02 cannot be built until S01 delivers these. The roadmap marks S01 as `[x]` but STATE.md shows it's still in planning phase — this is a stale artifact from a doctor recovery.

## Recommendation

Implement S02 after S01 is complete. The work breaks into two clean tasks:

1. **CLI flag** — Add `--top-n` Typer option to `scripts/run_screener.py`, pass value through to `run_pipeline(top_n=N)`. Add validation (must be positive integer). Tests via `typer.testing.CliRunner`.

2. **Display column** — Add "Perf 1M" column to `render_results_table()` in `screener/display.py`. Use a new `fmt_signed_pct()` formatter that includes `+`/`-` sign (existing `fmt_pct` omits the `+`). Tests via captured console output.

Both tasks are independent of each other and could be done in either order. Each is small enough for a single task.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | `typer.Option` with `Annotated` type hints | Already used for `--update-symbols`, `--verbose`, `--preset`, `--config` |
| Number formatting | `fmt_pct()` in `screener/display.py` | Existing pattern; extend for signed percentages |
| CLI testing | `typer.testing.CliRunner` | Already used in `tests/test_cli_screener.py` |
| Console capture in tests | `Console(file=StringIO(), width=120)` | Already used in `tests/test_display.py` |

## Existing Code and Patterns

- **`scripts/run_screener.py:56-73`** — `run()` function with existing Typer options. New `--top-n` follows the same `Annotated[type | None, typer.Option(...)]` pattern. The value passes directly to `run_pipeline(top_n=N)` at line ~98.
- **`screener/display.py:181-214`** — `render_results_table()` with column definitions and row building. "Perf 1M" column inserts between "HV%ile" and "Yield" (or after "RSI", before "HV%ile" — placement is a minor choice). Each column follows the pattern: `table.add_column(...)` then a corresponding value in `table.add_row(...)`.
- **`screener/display.py:123-132`** — `fmt_pct()` returns `"{value:.1f}%"` without sign. TOPN-05 requires `+3.1%` / `-5.2%` format, so a new `fmt_signed_pct()` is needed (or inline formatting).
- **`models/screened_stock.py`** — `ScreenedStock` dataclass. S01 will add `perf_1m: Optional[float] = None`. S02 reads this field for display only.
- **`screener/pipeline.py:1191-1200`** — `run_pipeline()` signature. S01 will add `top_n: int | None = None`. S02 passes the CLI value here.
- **`tests/test_cli_screener.py`** — CLI tests using `CliRunner` with heavy `@patch` decoration. New `--top-n` tests follow the same pattern: mock `run_pipeline`, invoke with `["--top-n", "20"]`, assert `run_pipeline` was called with `top_n=20`.
- **`tests/test_display.py:186-265`** — `TestResultsTable` class with `_make_passing_stocks()` helper. New tests add `perf_1m` to stock fixtures and assert "Perf 1M" column header and formatted values appear in output.
- **D015** — Console injection pattern: `render_results_table(stocks, console=console)` for testability.
- **D019** — Module-level imports in CLI entry points for `@patch` targets.

## Constraints

- **S01 must be complete first.** `ScreenedStock.perf_1m` and `run_pipeline(top_n=...)` don't exist yet.
- **`top_n` must be `Optional[int]`** — `None` means no cap (TOPN-06 backward compat).
- **`top_n` must be positive** — Typer can enforce `min=1` or we validate manually.
- **`fmt_pct` cannot be modified** — it's used everywhere for unsigned percentages. A new formatter is needed for signed display.
- **Column count in `add_row` must match `add_column` count** — Rich raises if mismatched. Tests catch this.
- **`_make_stock` helper in tests doesn't accept `perf_1m`** — needs a keyword argument added.
- **345 existing tests must continue passing** — no breaking changes to `ScreenedStock`, `render_results_table`, or CLI.

## Common Pitfalls

- **Typer `int | None` default** — Must use `typer.Option(default=None)` explicitly; Typer infers required if no default is set. The existing `preset` option demonstrates this pattern.
- **Rich column/row count mismatch** — Adding a column to `add_column` without a matching value in every `add_row` call causes a silent misalignment or crash. Both must be updated together.
- **Signed percentage formatting** — `f"{value:+.1f}%"` is the cleanest Python approach (`:+` format spec includes sign for positive values). No need for a conditional.
- **`perf_1m=None` display** — Must show "N/A", not crash. Follow the `hv_pct_str` pattern: `fmt_signed_pct(stock.perf_1m) if stock.perf_1m is not None else "N/A"`.
- **Test helper staleness** — `_all_pass_filters()` in test_display.py doesn't include `hv_percentile` or `earnings_proximity` in its filter list. Check if this matters for new tests (it shouldn't — perf_1m is a data field, not a filter).

## Open Risks

- **S01 not implemented** — The entire S02 scope is blocked until `perf_1m` and `top_n` exist. If S01 changes its interface (e.g., different field name, different parameter name), S02 must adapt. This risk is low given the boundary map is explicit.
- **`--top-n 0` edge case** — Should `0` be treated as "no cap" or an error? Recommend error (min=1). Typer's `min` constraint handles this cleanly.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer CLI | — | none relevant (standard Python CLI framework, well-documented) |
| Rich tables | — | none relevant (standard terminal formatting, patterns already established in codebase) |

No external skills needed — this slice uses established project patterns with no new technologies.

## Sources

- `scripts/run_screener.py` — existing CLI structure and Typer option patterns
- `screener/display.py` — existing column/row patterns and formatter functions
- `tests/test_cli_screener.py` — existing CLI test patterns with CliRunner + @patch
- `tests/test_display.py` — existing display test patterns with console capture
- `models/screened_stock.py` — ScreenedStock dataclass (S01 will add `perf_1m`)
- `.gsd/DECISIONS.md` — D015 (console injection), D019 (module-level imports), D042 (top_n CLI-only)
