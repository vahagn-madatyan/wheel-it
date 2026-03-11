# Phase 6: Packaging & Tech Debt Cleanup - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix missing pyproject.toml dependencies so fresh `pip install -e .` works, wire human-readable config validation errors into both CLI entry points, fix test isolation issues in credential and Finnhub tests, and clean up stale deferred-items.md. No new features, no new filters, no new CLI commands.

</domain>

<decisions>
## Implementation Decisions

### Config Error UX
- Catch `ValidationError` at CLI entry points (run-screener and run-strategy --screen), not in config_loader
- Call existing `format_validation_errors()` to format the errors
- Display as Rich Panel titled "Configuration Error" with bullet list of field errors
- Include fix hints footer: "See config/presets/ for valid examples or run-screener --preset conservative"
- Identical error formatting in both run-screener and run-strategy --screen

### Dependency Pinning
- Add `ta`, `pyyaml`, `pydantic` to pyproject.toml dependencies
- Use minimum version pinning (e.g., `ta>=0.11`, `pyyaml>=6.0`, `pydantic>=2.0`) matching existing pattern (rich>=14.0, typer>=0.9.0)
- Verify fix by running `pip install -e .` in a clean venv as part of plan verification

### Test Isolation Fix
- Fix test_credentials.py env leak by monkeypatching load_dotenv before importlib.reload (matches established Phase 1 pattern)
- Also fix the 4 FinnhubAPIException mock failures in test_finnhub_client.py (set mock_finnhub.FinnhubAPIException to real exception class)
- Full pytest run as verification to confirm no regressions

### Stale Artifact Cleanup
- Delete `.planning/phases/02-data-sources/deferred-items.md` (issue it documents will be fixed in this phase)
- No other cleanup beyond the 4 success criteria items

### Claude's Discretion
- Exact minimum version numbers for ta, pyyaml, pydantic (based on what's currently installed / API compatibility)
- Specific monkeypatch approach for load_dotenv in credential tests
- How to structure the ValidationError catch block (try/except scope)

</decisions>

<specifics>
## Specific Ideas

- The Rich Panel for config errors should feel consistent with existing screener output (Phase 4 established Rich console patterns)
- Error messages should be actionable: show the field name, what's wrong, and what valid values look like
- The clean venv verification is important -- this is the primary deliverable of the phase

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `screener/config_loader.py`: `format_validation_errors()` already exists, just needs to be called from CLI entry points
- `screener/config_loader.py`: `load_config()` raises `ValidationError` on invalid config (Pydantic)
- `scripts/run_screener.py`: Typer CLI entry point -- add try/except around config loading
- `scripts/run_strategy.py`: Typer CLI entry point with --screen flag -- same try/except pattern

### Established Patterns
- `monkeypatch + importlib.reload` for module-level env var testing (Phase 1 decision)
- Rich Console injection via parameter for testability (Phase 4 decision)
- Minimum version pinning in pyproject.toml (rich>=14.0, typer>=0.9.0)
- All render functions accept optional Console parameter

### Integration Points
- `pyproject.toml` [project.dependencies] -- add 3 new entries
- `scripts/run_screener.py` -- wrap config loading in try/except ValidationError
- `scripts/run_strategy.py` -- same wrap for --screen path
- `tests/test_credentials.py` -- monkeypatch load_dotenv
- `tests/test_finnhub_client.py` -- fix FinnhubAPIException mock
- `.planning/phases/02-data-sources/deferred-items.md` -- delete

</code_context>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 06-packaging-cleanup*
*Context gathered: 2026-03-10*
