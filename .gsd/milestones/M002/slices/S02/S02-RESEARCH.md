# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 is a low-risk wiring slice that connects S01's pipeline changes (`top_n` parameter, `perf_1m` field) to the user-facing surfaces: a `--top-n` Typer CLI option on `run-screener` and a "Perf 1M" column in the Rich results table. All heavy lifting (perf computation, sort/cap logic, two-pass pipeline architecture) was completed in S01 on branch `gsd/M002/S01`. S02 needs to merge that branch first, then add ~20 lines of production code and corresponding tests.

The critical prerequisite is that **`gsd/M002/S01` must be merged into `gsd/M002/S02` before implementation begins** — the S02 branch currently lacks `perf_1m` on `ScreenedStock`, `compute_monthly_performance()` in `market_data.py`, and the `top_n` parameter on `run_pipeline()`.

## Recommendation

Merge `gsd/M002/S01` into `gsd/M002/S02`, then implement three small changes:

1. **CLI flag** — Add `top_n: int | None` Typer option to `scripts/run_screener.py:run()`, pass it through to `run_pipeline(top_n=top_n)`. Follow the existing `--verbose` / `--preset` Annotated pattern.
2. **Display column** — Add `"Perf 1M"` column to `render_results_table()` in `screener/display.py`, using `fmt_pct(stock.perf_1m)` with sign formatting. Insert after "HV%ile" and before "Yield" to group technical indicators together.
3. **Tests** — CLI flag parsing test (Typer CliRunner), pipeline passthrough verification, display column presence, sign formatting for positive/negative/None values.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option definition | Typer `Annotated[int \| None, typer.Option()]` | Already used for `--preset`, `--config`, `--verbose` in same file |
| CLI testing | `typer.testing.CliRunner` | Already used in `test_cli_screener.py` with mock-heavy pattern |
| Percentage formatting | `screener.display.fmt_pct()` | Already handles None→"N/A", consistent with HV%ile and Yield columns |
| Console capture for display tests | `Console(file=StringIO(), width=120)` | Pattern established in `test_display.py` |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — CLI entry point using Typer `Annotated` pattern. Add `top_n` parameter mirroring existing `verbose`/`preset` options. Pass to `run_pipeline(top_n=top_n)` in the `with progress_context()` block (line ~95).
- `screener/display.py:render_results_table()` — Rich table with 13 columns. New "Perf 1M" column at position after "HV%ile" (line 190). Row data uses `fmt_pct()` for percentage fields — reuse for `perf_1m`. Sign is inherent in the value (e.g. -5.2 → "-5.2%", 3.1 → "3.1%").
- `tests/test_cli_screener.py` — Mock-heavy CLI tests patching at `scripts.run_screener.*` module level. The `test_default_no_file_writes` pattern shows how to verify `run_pipeline` is called with specific kwargs — extend to verify `top_n` passthrough.
- `tests/test_display.py` — `_make_stock()` helper, `_all_pass_filters()` helper, `_capture_console()` helper. Add `perf_1m` parameter to `_make_stock()` or set directly on ScreenedStock instances.
- `screener/display.py:fmt_pct()` — Formats `float | None` as "X.X%" or "N/A". Handles negative values correctly (`-3.7%`). Already used for HV%ile and Yield; reuse for Perf 1M.

## Constraints

- **Branch dependency**: `gsd/M002/S01` contains all prerequisite code changes (`perf_1m` field, `top_n` parameter, `compute_monthly_performance()`). Must merge before implementing S02.
- **`top_n` must be `int | None`**: `None` means no cap (TOPN-06 backward compat). Typer renders `None` default as "no value" in help text automatically.
- **`top_n` should accept only positive integers**: Typer doesn't validate `min=1` natively — will need a `typer.Option(min=1)` or a manual validation check. Typer's `min` parameter works for `int` options.
- **Column ordering matters**: "Perf 1M" should go near other technical indicators (after HV%ile) so the table reads logically: technicals → options → scoring.
- **`fmt_pct` sign behavior**: `fmt_pct(-5.2)` → `"-5.2%"` and `fmt_pct(3.1)` → `"3.1%"` (no `+` prefix). The requirement says "formatted as percentage with sign (e.g. -5.2%, +3.1%)" — may want explicit `+` for positive values. This is a minor display choice; a small wrapper or inline format would handle it.
- **345 existing tests must remain green** after changes.

## Common Pitfalls

- **Forgetting to merge S01 branch** — S02 branch has no `perf_1m` or `top_n`. Attempting to implement without merge will fail imports. Merge S01 first, run tests to confirm green.
- **`fmt_pct` doesn't add `+` for positives** — `fmt_pct(3.1)` returns `"3.1%"` not `"+3.1%"`. If requirement TOPN-05 strictly needs `+` prefix, add a `fmt_perf()` wrapper or adjust inline. The `+` sign is nice-to-have for readability but not blocking.
- **Typer `int | None` requires `None` default explicitly** — `typer.Option(default=None)` is needed. If the default is omitted, Typer may treat it as required. Follow the `preset` option pattern which already uses `| None` with `None` default.
- **Mock patch target for `run_pipeline`** — Must patch at `scripts.run_screener.run_pipeline`, not at `screener.pipeline.run_pipeline`, because the CLI module imports it directly (D019 pattern).

## Open Risks

- **S01 branch merge conflicts** — The `gsd/M002/S01` branch modifies `screener/pipeline.py`, `models/screened_stock.py`, `screener/market_data.py`, and `tests/test_pipeline.py`. The S02 branch has only `.gsd/` file changes since the common ancestor (`cd06247`), so merge should be clean. Verify with `git merge --no-commit` first.
- **Positive sign display ambiguity** — TOPN-05 says "formatted as percentage with sign (e.g. -5.2%, +3.1%)" suggesting explicit `+` for positive values. Current `fmt_pct` doesn't add `+`. Low risk — either add a 2-line helper or accept `3.1%` without `+`.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | — | none found (standard lib-level CLI framework, no skill needed) |
| Rich | — | none found (already well-established patterns in codebase) |

## Sources

- S01 branch diff: `git diff HEAD...gsd/M002/S01 --stat` (16 files, +912 lines)
- S01/T01 commit `815541d`: `perf_1m` field + `compute_monthly_performance()` + 6 tests
- S01/T02 commit `94af363`: two-pass pipeline with `top_n` sort/cap + 267 lines of pipeline tests
- Existing CLI tests: `tests/test_cli_screener.py` (5 tests, Typer CliRunner + mock pattern)
- Existing display tests: `tests/test_display.py` (30+ tests, console capture pattern)
- Decisions register: D042 (top_n is CLI-only), D044 (None perf_1m sorts last)
