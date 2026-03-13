# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 is a low-risk wiring slice that connects S01's backend work (perf computation, sort/cap, `top_n` pipeline parameter) to the user-facing layer: a `--top-n` Typer CLI option on `run-screener` and a "Perf 1M" column in the Rich results table. All backend logic already exists on the `gsd/M002/S01` branch — S02 just passes the flag through and renders the field.

The three requirements owned by this slice (TOPN-01 primary, TOPN-05, TOPN-06) are straightforward. The existing codebase has clear, well-tested patterns for both CLI options (4 existing `Annotated[..., typer.Option()]` params) and display columns (12 existing columns with formatters). The work is mechanical: add one Typer option, thread it to `run_pipeline()`, add one column + one row value, write tests following established patterns.

**Critical prerequisite:** S01's code changes (on branch `gsd/M002/S01`) must be merged into this branch before implementation. The `perf_1m` field on `ScreenedStock` and the `top_n` parameter on `run_pipeline()` do not exist on the current `gsd/M002/S02` branch.

## Recommendation

Merge S01 first, then implement in two focused tasks:

1. **CLI flag** — Add `--top-n` Typer option, pass to `run_pipeline(top_n=N)`, add tests for flag parsing and pipeline passthrough. Follow the exact pattern of existing CLI options (see `update_symbols`, `verbose`, `preset`).

2. **Display column** — Add "Perf 1M" column to `render_results_table()` between "HV%ile" and "Yield", using a new `fmt_signed_pct()` formatter that adds explicit `+` sign for positive values (per TOPN-05: "e.g. -5.2%, +3.1%"). Add tests for column presence, formatting, and None handling.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option declaration | Typer `Annotated[..., typer.Option()]` pattern | 4 existing options in `run_screener.py` use this exact pattern |
| Display formatting | `fmt_pct()` in `screener/display.py` | Handles None → "N/A" and `%.1f%` format; extend for signed variant |
| Console capture in tests | `Console(file=StringIO(), width=120)` pattern | Used in all 25+ display tests via `_capture_console()` |
| CLI test runner | `typer.testing.CliRunner` | Used in all 4 existing CLI screener tests |
| Mocking pipeline calls | `@patch("scripts.run_screener.run_pipeline")` | Existing `test_cli_screener.py` patches at module import level per D019 |

## Existing Code and Patterns

- `scripts/run_screener.py` L57-73 — Four existing `Annotated[..., typer.Option()]` declarations. The `--top-n` option follows this exact pattern. Note: `int | None` type with `None` default for backward compatibility.
- `scripts/run_screener.py` L119-126 — `run_pipeline()` call site. Add `top_n=top_n` kwarg here. S01 already added the `top_n` parameter to the function signature.
- `screener/display.py` L181-193 — Column declarations via `table.add_column()`. Insert "Perf 1M" column. Current order: `#, Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, HV%ile, Yield, Score, Sector`.
- `screener/display.py` L201-216 — Row data via `table.add_row()`. Must add `perf_1m` value in matching column position.
- `screener/display.py` L128-133 — `fmt_pct()` formatter. Handles `None → "N/A"` and `f"{value:.1f}%"` but does NOT add `+` for positive values. TOPN-05 requires signed format ("+3.1%"), so a new `fmt_signed_pct()` or inline formatting is needed.
- `tests/test_display.py` L56-65 — `_make_stock()` helper. Must add `perf_1m` param.
- `tests/test_display.py` L68-77 — `_all_pass_filters()`. No change needed — filter set is unrelated to display.
- `tests/test_cli_screener.py` L37-73 — `test_default_no_file_writes` pattern. Heavy mock stacking (`@patch` decorators) for CLI tests. Follow this exactly for `--top-n` tests.
- `models/screened_stock.py` L26 — `perf_1m: Optional[float] = None` field (added by S01, not yet on this branch).

## Constraints

- **S01 merge required:** `ScreenedStock.perf_1m` and `run_pipeline(top_n=...)` don't exist on this branch yet. Merge `gsd/M002/S01` before any implementation.
- **Column count limit:** Table already has 13 columns. Adding "Perf 1M" makes 14 — watch terminal width. Place between "HV%ile" and "Yield" since perf is a technical indicator closely related to these.
- **`add_row` positional args:** Rich `table.add_row()` is positional — the new value must be inserted at the exact position matching the new column. Off-by-one here silently shifts all subsequent columns.
- **`fmt_pct` doesn't show `+` sign:** Current `fmt_pct(-5.2)` → `"-5.2%"` but `fmt_pct(3.1)` → `"3.1%"` (no plus). TOPN-05 requires explicit `+` for positive values. Need a signed variant.
- **Backward compatibility (TOPN-06):** `--top-n` must be optional with `None` default. When absent, `run_pipeline` receives `top_n=None` and processes all stocks. Existing tests must continue passing without modification.
- **Test count floor:** 345 existing tests must continue to pass.

## Common Pitfalls

- **Forgetting to merge S01 first** — All S02 code depends on `perf_1m` field and `top_n` parameter that only exist on the S01 branch. Without merge, imports fail.
- **`add_row` column mismatch** — Rich's `table.add_row(*values)` is strictly positional. If the "Perf 1M" column is added at position N but the value is inserted at position N+1 (or vice versa), every column after it displays wrong data with no error. Must count carefully.
- **Typer `int | None` default** — Typer handles `Optional[int]` with `None` default, but the type annotation must use `int | None` (not bare `int`) to allow no-flag invocation. The existing `preset` option uses `PresetName | None = None` as the model.
- **Test mock stacking order** — `@patch` decorators are applied bottom-up. The existing `test_cli_screener.py` tests have 8+ stacked decorators. New tests must include all patches to avoid real API calls. Copy the exact decorator stack from `test_default_no_file_writes`.
- **Signed percentage for zero** — `+0.0%` looks odd. Decide: treat zero as unsigned `0.0%` or show `+0.0%`. Recommendation: `+0.0%` for consistency (zero is non-negative).

## Open Risks

- **S01 merge conflicts** — S01 modifies `screener/pipeline.py`, `models/screened_stock.py`, `screener/market_data.py`, and `tests/`. If this branch has diverged, merge conflicts are possible. Risk: low (S02 branch has only `.gsd/` file changes so far, no code changes).
- **Terminal width overflow** — 14 columns may wrap on narrower terminals (< 120 chars). This is cosmetic, not functional. The existing tests use `width=120` consoles which should accommodate 14 columns.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer (CLI) | — | none found (well-known library, no skill needed) |
| Rich (display) | — | none found (well-known library, no skill needed) |
| pytest | — | none found (well-known library, no skill needed) |

## Sources

- `scripts/run_screener.py` — existing CLI option patterns (4 options, Typer runner)
- `screener/display.py` — existing column/row patterns (13 columns, formatters)
- `tests/test_display.py` — 25 display tests with console capture pattern
- `tests/test_cli_screener.py` — 4 CLI tests with mock stacking pattern
- `git diff main..gsd/M002/S01` — S01 deliverables (perf_1m field, top_n param, sort/cap logic, 6 new top-N pipeline tests, 7 new perf computation tests)
- `models/screened_stock.py` — ScreenedStock dataclass (S01 adds perf_1m field)
- `.gsd/DECISIONS.md` — D041 (22-day lookback), D042 (CLI-only), D043 (cap placement), D044 (None sorts last)
