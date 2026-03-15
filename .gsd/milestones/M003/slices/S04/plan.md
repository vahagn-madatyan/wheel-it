# S04: End-to-End Strategy Verification

**Goal:** Verify the complete wheel cycle works end-to-end with all legacy code removed — positions detected, calls sold via `screen_calls()`, puts sold via `screen_puts()`, no dead imports.
**Demo:** `run-strategy --help` works, all tests pass, `rg` confirms zero references to any deleted module, and strategy integration tests exercise the full put + call screening paths.

## Must-Haves

- `run-strategy --help` exits 0 and shows all flags
- Zero references to `core/strategy`, `core/execution`, or `models/contract` anywhere in codebase (including tests, scripts, and config)
- Strategy test covers: `long_shares` → `screen_calls()` path, allowed symbols → `screen_puts()` path, `fresh_start` mode
- All tests pass (368+ existing + new put screener tests)

## Verification

- `python -m pytest tests/ -q` — all tests pass, zero failures
- `rg "core.strategy|core.execution|models.contract" . --glob '*.py' -l` — zero files
- `run-strategy --help` — exits 0

## Tasks

- [ ] **T01: Final integration sweep and test confirmation** `est:30m`
  - Why: Ensures the complete wheel strategy works after all changes — the proof that M003 delivered
  - Files: `tests/test_cli_strategy.py`, any remaining fixups
  - Do: Run full test suite. Search for any remaining references to deleted modules. Verify `run-strategy --help` works. Review `test_cli_strategy.py` to confirm both call and put screener paths are tested. If any test imports deleted modules, fix or remove them. Confirm `pyproject.toml` has `run-put-screener` entry point. Run `rg` checks for dead references. Write milestone summary notes.
  - Verify: `python -m pytest tests/ -q` — all pass; `rg "core.strategy|core.execution|models.contract" . --glob '*.py'` — zero matches
  - Done when: Full test suite passes, zero dead references, `run-strategy --help` works

## Files Likely Touched

- `tests/test_cli_strategy.py` (possible fixups)
- Any files with remaining dead references
