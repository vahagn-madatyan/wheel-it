---
estimated_steps: 7
estimated_files: 4
---

# T01: Build run-put-screener CLI entry point

**Slice:** S02 — Put Screener CLI + Strategy Integration
**Milestone:** M003

## Description

Create the `run-put-screener` standalone CLI mirroring `run-call-screener`, register it in `pyproject.toml`, and write CLI tests.

## Steps

1. Read `scripts/run_call_screener.py` to confirm the CLI pattern.
2. Create `scripts/run_put_screener.py` with Typer app. Arguments: `symbols` (variadic positional, `list[str]`), `--buying-power` (required float), `--preset` (optional enum: conservative/moderate/aggressive), `--config` (optional path, default "config/screener.yaml").
3. Implement the command: uppercase symbols, load config (same `load_config`/`load_preset`/`deep_merge` pattern), create broker client via `create_broker_client()`, call `screen_puts()`, call `render_put_results_table()`.
4. Handle `ValidationError` with Rich Panel error display (same pattern as call screener).
5. Add `run-put-screener = "scripts.run_put_screener:main"` to `pyproject.toml` `[project.scripts]`.
6. Write CLI tests in `tests/test_put_screener.py`: help text shows flags, symbol uppercasing works, preset override works.
7. Run `pip install -e .` to register the new entry point, then verify `run-put-screener --help`.

## Must-Haves

- [ ] `run-put-screener --help` exits 0 and shows `--buying-power`, `--preset`, `--config`, and `SYMBOLS` in help text
- [ ] Symbols are uppercased before passing to `screen_puts()`
- [ ] `run-put-screener` registered in `pyproject.toml` `[project.scripts]`
- [ ] CLI tests pass

## Verification

- `run-put-screener --help` — exits 0 with expected flags
- `python -m pytest tests/test_put_screener.py -v -k cli` — CLI tests pass

## Inputs

- `screener/put_screener.py` — `screen_puts()` and `render_put_results_table()` from S01
- `scripts/run_call_screener.py` — CLI template

## Expected Output

- `scripts/run_put_screener.py` — Typer CLI entry point
- `pyproject.toml` — new `run-put-screener` entry
- `tests/test_put_screener.py` — extended with CLI tests
