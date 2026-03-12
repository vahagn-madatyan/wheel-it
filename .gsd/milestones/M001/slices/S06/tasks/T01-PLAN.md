# T01: 06-packaging-cleanup 01

**Slice:** S06 — **Milestone:** M001

## Description

Fix all four tech debt items identified in the v1.0 audit: add missing pyproject.toml dependencies (ta, pyyaml, pydantic), wire human-readable config validation errors into both CLI entry points, fix test isolation leak in credential tests, and remove stale deferred-items.md.

Purpose: Ensure fresh `pip install -e .` works, CLI errors are user-friendly, and the test suite is green regardless of local .env contents.
Output: Updated pyproject.toml, both CLI scripts with error handling, fixed test file, deleted stale artifact.

## Must-Haves

- [ ] "Running pip install -e . in a clean venv installs ta, pyyaml, and pydantic without errors"
- [ ] "Invalid screener.yaml produces a Rich Panel titled 'Configuration Error' with bullet-style field errors in both run-screener and run-strategy --screen"
- [ ] "pytest tests/test_credentials.py passes regardless of whether .env contains real API keys"
- [ ] "deferred-items.md no longer exists in the 02-data-sources phase directory"

## Files

- `pyproject.toml`
- `scripts/run_screener.py`
- `scripts/run_strategy.py`
- `tests/test_credentials.py`
- `tests/test_cli_screener.py`
- `tests/test_cli_strategy.py`
