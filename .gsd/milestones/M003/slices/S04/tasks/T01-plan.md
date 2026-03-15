---
estimated_steps: 5
estimated_files: 2
---

# T01: Final integration sweep and test confirmation

**Slice:** S04 — End-to-End Strategy Verification
**Milestone:** M003

## Description

Final verification that the complete wheel strategy works end-to-end after all M003 changes. Confirms zero dead references, all tests pass, and both screening paths (calls and puts) are exercised in strategy tests.

## Steps

1. Run `python -m pytest tests/ -q` — confirm all tests pass with zero failures.
2. Run `rg "core.strategy|core.execution|models.contract" . --glob '*.py' -l` — confirm zero files reference deleted modules.
3. Run `rg "YIELD_MIN|YIELD_MAX|SCORE_MIN|OPEN_INTEREST_MIN|EXPIRATION_MIN|EXPIRATION_MAX" . --glob '*.py'` — confirm zero matches.
4. Run `run-strategy --help` — confirm exits 0 with all expected flags.
5. Review `tests/test_cli_strategy.py` to confirm both `screen_calls()` and `screen_puts()` paths are tested in strategy integration tests. If any path is untested, add the test. Run final full test suite.

## Must-Haves

- [ ] `python -m pytest tests/ -q` — all pass, zero failures
- [ ] Zero `.py` files reference `core.strategy`, `core.execution`, or `models.contract`
- [ ] Zero `.py` files reference obsolete `config/params.py` constants
- [ ] `run-strategy --help` exits 0
- [ ] Strategy tests cover both `screen_calls()` and `screen_puts()` code paths

## Verification

- `python -m pytest tests/ -q` — all pass
- `rg "core.strategy|core.execution|models.contract" . --glob '*.py'` — zero matches
- `run-strategy --help` — exits 0

## Inputs

- Complete codebase after S01–S03
- All prior task summaries

## Expected Output

- Verified clean codebase
- Possible minor test additions if gaps found
- Milestone summary ready to write
