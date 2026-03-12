---
id: S06
parent: M001
milestone: M001
provides:
  - Complete pyproject.toml dependency list (ta, pyyaml, pydantic)
  - Human-readable config validation error panels in both CLI entry points
  - Isolated credential tests independent of local .env
  - Removed stale deferred-items.md artifact
requires: []
affects: []
key_files: []
key_decisions:
  - "Patch dotenv.load_dotenv at source module (not config.credentials.load_dotenv) because reload creates fresh binding"
  - "Console(stderr=True) for error output, typer.Exit(code=1) for clean CLI exit on validation failure"
patterns_established:
  - "ValidationError catch pattern: try/except around config loading, format with format_validation_errors, display as Rich Panel titled 'Configuration Error'"
observability_surfaces: []
drill_down_paths: []
duration: 3min
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---
# S06: Packaging Cleanup

**# Phase 06 Plan 01: Packaging & Tech Debt Cleanup Summary**

## What Happened

# Phase 06 Plan 01: Packaging & Tech Debt Cleanup Summary

**Added missing pyproject.toml deps (ta, pyyaml, pydantic), wired Rich Panel config validation errors into both CLIs, fixed credential test env leak, removed stale artifact**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-11T18:18:29Z
- **Completed:** 2026-03-11T18:21:25Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- pyproject.toml now declares all runtime dependencies -- fresh `pip install -e .` works without manual installs
- Both `run-screener` and `run-strategy --screen` display a Rich Panel titled "Configuration Error" with formatted field errors and fix hints when config validation fails
- credential tests (test_finnhub_key_loaded, test_finnhub_key_missing_is_none) now pass regardless of .env contents by patching dotenv.load_dotenv before reload
- Stale `.planning/phases/02-data-sources/deferred-items.md` removed (issue already resolved)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add missing dependencies and delete stale artifact** - `0d965df` (chore)
2. **Task 2: Fix test_credentials.py env leak** - `edaeb48` (fix)
3. **Task 3: Wire config validation errors into CLI entry points** - `2b4420d` (test/RED), `5dbbcbe` (feat/GREEN)

_TDD task 3 has two commits: RED (failing tests) then GREEN (implementation)._

## Files Created/Modified
- `pyproject.toml` - Added ta>=0.11, pyyaml>=6.0, pydantic>=2.0 to dependencies
- `scripts/run_screener.py` - Added try/except ValidationError with Rich Panel around config loading
- `scripts/run_strategy.py` - Added try/except ValidationError with Rich Panel around load_config() in --screen path
- `tests/test_credentials.py` - Added monkeypatch.setattr("dotenv.load_dotenv", ...) to isolate from real .env
- `tests/test_cli_screener.py` - Added test_config_error_shows_panel test
- `tests/test_cli_strategy.py` - Added test_config_error_shows_panel_with_screen test

## Decisions Made
- Patched `dotenv.load_dotenv` at the source module level (not at `config.credentials.load_dotenv`) because `importlib.reload()` creates a fresh binding from the dotenv package
- Used `Console(stderr=True)` so validation errors go to stderr, consistent with error semantics
- Used `typer.Exit(code=1)` instead of `sys.exit(1)` since both CLIs use Typer framework

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All four v1.0 audit tech debt items resolved
- Full test suite green (193 tests, 0 failures)
- No remaining deferred items or known tech debt

## Self-Check: PASSED

All 6 files verified present. All 4 commits verified in git log. deferred-items.md confirmed removed. 193/193 tests passing.

---
*Phase: 06-packaging-cleanup*
*Completed: 2026-03-11*
