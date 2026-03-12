# S06: Packaging Cleanup

**Goal:** Fix all four tech debt items identified in the v1.
**Demo:** Fix all four tech debt items identified in the v1.

## Must-Haves


## Tasks

- [x] **T01: 06-packaging-cleanup 01** `est:3min`
  - Fix all four tech debt items identified in the v1.0 audit: add missing pyproject.toml dependencies (ta, pyyaml, pydantic), wire human-readable config validation errors into both CLI entry points, fix test isolation leak in credential tests, and remove stale deferred-items.md.

Purpose: Ensure fresh `pip install -e .` works, CLI errors are user-friendly, and the test suite is green regardless of local .env contents.
Output: Updated pyproject.toml, both CLI scripts with error handling, fixed test file, deleted stale artifact.

## Files Likely Touched

- `pyproject.toml`
- `scripts/run_screener.py`
- `scripts/run_strategy.py`
- `tests/test_credentials.py`
- `tests/test_cli_screener.py`
- `tests/test_cli_strategy.py`
