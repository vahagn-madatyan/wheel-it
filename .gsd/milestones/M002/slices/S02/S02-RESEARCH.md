# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 wires the S01 pipeline work (`top_n` parameter, `perf_1m` field) into user-facing surfaces: a `--top-n` Typer CLI option on `run-screener` and a "Perf 1M" column in the Rich results table. Both changes are mechanically straightforward — they follow established patterns already used for `--verbose`, `--preset`, `--update-symbols` (CLI) and `HV%ile`, `Yield` (display columns).

The S01 branch (`gsd/M002/S01`) has not been merged into S02's branch yet. S02 must incorporate S01's changes first (merge or rebase). S01 added `perf_1m` to `ScreenedStock`, `compute_monthly_performance()` to `market_data.py`, and the `top_n` parameter + two-pass architecture to `run_pipeline()` — all with 12 passing tests.

The main risk is purely procedural: ensuring S01's branch changes are present before starting. The code changes themselves are minimal (~15 lines for CLI, ~5 lines for display, ~60 lines for tests).

## Recommendation

Merge S01 branch into S02, then implement three small changes:

1. **CLI**: Add `top_n: Annotated[int | None, typer.Option("--top-n", ...)] = None` parameter to `run()` and pass it through to `run_pipeline(top_n=top_n)`.
2. **Display**: Add `table.add_column("Perf 1M", justify="right")` between "HV%ile" and "Yield", with `fmt_pct(stock.perf_1m)` in the row. Use `fmt_pct` with sign formatting (requires a small `fmt_pct_signed` helper or inline format since existing `fmt_pct` doesn't show `+` prefix).
3. **Tests**: CLI flag parsing tests (help shows `--top-n`, flag passes through to `run_pipeline`, no flag means `top_n=None`), display column tests ("Perf 1M" header present, values rendered correctly for positive/negative/None).

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | Typer `typer.Option("--top-n")` | Already used for `--verbose`, `--preset`, `--config`, `--update-symbols` |
| Results table column | Rich `table.add_column()` + `table.add_row()` | Pattern established for all 12 existing columns |
| Percentage formatting | `screener.display.fmt_pct()` | Already handles None → "N/A" |
| CLI test runner | `typer.testing.CliRunner` | Already used in `test_cli_screener.py` |
| Console capture | `Console(file=StringIO(), width=120)` | Already used in `test_display.py` |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — All CLI options use `Annotated[type, typer.Option(...)]` pattern. S02 adds one more. The `run_pipeline()` call at line 119 needs `top_n=top_n` kwarg added.
- `screener/display.py:render_results_table()` — Columns added via `table.add_column()` (lines 181-193), rows via `table.add_row()` (lines 202-215). "Perf 1M" inserts between "HV%ile" and "Yield" to group technical indicators together.
- `screener/display.py:fmt_pct()` — Returns `f"{value:.1f}%"` or "N/A". Doesn't show `+` sign for positive values. For Perf 1M, either use a new `fmt_pct_signed()` helper or format inline with `f"{value:+.1f}%"` for the sign prefix (requirement TOPN-05: "Formatted as percentage with sign").
- `tests/test_cli_screener.py` — Uses `@patch("scripts.run_screener.run_pipeline")` pattern with `CliRunner`. All tests mock the full dependency chain (broker, finnhub, pipeline, display). S02 tests follow identical structure.
- `tests/test_display.py:_make_stock()` — Helper creates `ScreenedStock` with arbitrary fields. Currently missing `perf_1m` kwarg — needs adding. `_all_pass_filters()` provides passing filter results.
- `models/screened_stock.py` — S01 adds `perf_1m: Optional[float] = None` after `hv_percentile` in the Technical indicators section.
- `screener/pipeline.py:run_pipeline()` — S01 adds `top_n: int | None = None` parameter. CLI just passes through.

## Constraints

- S01 branch must be merged before any S02 code changes — `perf_1m` field and `top_n` parameter don't exist on current branch.
- `--top-n` must accept positive integers only. Typer's `int | None` with `None` default handles the "omitted" case. Validation for `top_n >= 1` should happen at CLI level (Typer callback or early guard).
- Column order matters — "Perf 1M" goes between "HV%ile" and "Yield" to group technical/performance metrics logically, before scoring columns.
- Sign formatting: TOPN-05 specifies `"-5.2%"` and `"+3.1%"` — existing `fmt_pct` doesn't produce the `+` prefix for positive values. Need a signed variant.
- Typer 0.24.1 is installed — `Annotated` syntax with `typer.Option` is fully supported.
- 345 existing tests on current branch (357 with S01's 12 new tests merged).

## Common Pitfalls

- **Forgetting S01 merge** — All three S02 files depend on S01 code (`perf_1m` field, `top_n` param). Must merge first or tests will fail with `AttributeError`.
- **Column/row count mismatch** — `add_column()` count must match `add_row()` argument count exactly. Adding "Perf 1M" column requires adding the corresponding value in `add_row()` at the matching position.
- **Mock call assertion for top_n** — When testing CLI passthrough, `mock_pipeline.assert_called_once()` isn't enough. Need to verify `top_n=20` is in the kwargs: `mock_pipeline.call_args` inspection or `assert_called_with(..., top_n=20)`.
- **test_display.py _make_stock helper** — Existing helper doesn't accept `perf_1m`. Need to add it or tests can't set the field for display verification.
- **Negative zero** — `fmt_pct_signed` with `-0.0` could display as `"-0.0%"` — use `value or 0.0` if cosmetically undesirable, though this is minor.

## Open Risks

- **S01 merge conflicts** — S01 modified `pipeline.py`, `market_data.py`, `screened_stock.py`, and `test_pipeline.py`. The S02 branch may have diverged. Conflicts should be minimal since S02 hasn't touched those files, but verify after merge.
- **Existing display tests** — Adding a column changes table output width. Existing tests check for column header presence (`assert "Symbol" in output`) which should still pass, but any tests that depend on exact output formatting could break. Review `test_display.py` for fragile assertions — current tests use substring checks, so safe.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer (CLI) | No relevant skill found | none found |
| Rich (tables) | No relevant skill found | none found |
| Python testing | No relevant skill found | none found |

No useful skills exist for this slice's narrow scope (Typer option + Rich column). The codebase already has complete working patterns for both.

## Sources

- S01 task summaries on `gsd/M002/S01` branch — confirmed `perf_1m`, `top_n`, and two-pass pipeline are implemented with 12 tests
- `scripts/run_screener.py` — current CLI structure with 4 existing options
- `screener/display.py` — current table with 12 columns, `fmt_pct` helper
- `tests/test_cli_screener.py` — 5 existing CLI tests using CliRunner + mock pattern
- `tests/test_display.py` — display test helpers and 30+ existing tests
