# Phase 6: Packaging & Tech Debt Cleanup - Research

**Researched:** 2026-03-11
**Domain:** Python packaging (pyproject.toml), Pydantic error handling, pytest test isolation
**Confidence:** HIGH

## Summary

Phase 6 is a well-scoped tech debt cleanup phase with four discrete deliverables: (1) add three missing dependencies to pyproject.toml, (2) catch Pydantic ValidationErrors at CLI entry points and display them as Rich Panels, (3) fix test_credentials.py env leak caused by `load_dotenv(override=True)` during `importlib.reload`, and (4) delete a stale deferred-items.md file.

All four items are low-risk, low-complexity changes to existing code. The codebase already has `format_validation_errors()` ready to use, Rich Panel rendering patterns in `screener/display.py`, and the monkeypatch + reload test pattern established in Phase 1. The finnhub_client test issue mentioned in the deferred-items.md has already been fixed (all 21 tests pass), so that file is truly stale and can simply be deleted.

**Primary recommendation:** Implement all four items in a single plan since they are independent, small changes touching different files with no interdependencies.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Catch `ValidationError` at CLI entry points (run-screener and run-strategy --screen), not in config_loader
- Call existing `format_validation_errors()` to format the errors
- Display as Rich Panel titled "Configuration Error" with bullet list of field errors
- Include fix hints footer: "See config/presets/ for valid examples or run-screener --preset conservative"
- Identical error formatting in both run-screener and run-strategy --screen
- Add `ta`, `pyyaml`, `pydantic` to pyproject.toml dependencies
- Use minimum version pinning (e.g., `ta>=0.11`, `pyyaml>=6.0`, `pydantic>=2.0`) matching existing pattern (rich>=14.0, typer>=0.9.0)
- Verify fix by running `pip install -e .` in a clean venv as part of plan verification
- Fix test_credentials.py env leak by monkeypatching load_dotenv before importlib.reload (matches established Phase 1 pattern)
- Also fix the 4 FinnhubAPIException mock failures in test_finnhub_client.py (set mock_finnhub.FinnhubAPIException to real exception class)
- Full pytest run as verification to confirm no regressions
- Delete `.planning/phases/02-data-sources/deferred-items.md` (issue it documents will be fixed in this phase)
- No other cleanup beyond the 4 success criteria items

### Claude's Discretion
- Exact minimum version numbers for ta, pyyaml, pydantic (based on what's currently installed / API compatibility)
- Specific monkeypatch approach for load_dotenv in credential tests
- How to structure the ValidationError catch block (try/except scope)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

## Standard Stack

### Core (Already Installed)

| Library | Installed Version | Min Version for pyproject.toml | Purpose |
|---------|-------------------|-------------------------------|---------|
| ta | 0.11.0 | `ta>=0.11` | Technical analysis indicators (RSI, SMA) |
| PyYAML | 6.0.3 | `pyyaml>=6.0` | YAML config file parsing |
| pydantic | 2.12.5 | `pydantic>=2.0` | Config validation with field validators |
| rich | (already declared) | `rich>=14.0` | Panel rendering for error display |
| pytest | 9.0.2 | (dev dependency) | Test framework |

### Version Pin Rationale (Claude's Discretion Resolution)

**Confidence: HIGH** -- versions verified from `pip show` output of current environment.

| Library | Pin | Reasoning |
|---------|-----|-----------|
| `ta>=0.11` | 0.11.0 is the only stable release; project uses `ta.momentum.RSIIndicator` and `ta.trend.SMAIndicator` which exist since 0.7+ |
| `pyyaml>=6.0` | 6.0 introduced safe_load as default behavior; project uses `yaml.safe_load` and `yaml.dump` exclusively |
| `pydantic>=2.0` | Project uses v2 API: `model_validate()`, `field_validator`, `BaseModel` -- all v2-only features. Cannot use v1. |

### No New Libraries Needed

This phase adds no new dependencies. All three libraries are already installed and used extensively -- they were simply omitted from pyproject.toml.

## Architecture Patterns

### Pattern 1: ValidationError Catch at CLI Entry Points

**What:** Wrap config loading calls in try/except `ValidationError`, format with existing helper, display as Rich Panel, then `raise typer.Exit(code=1)`.

**Where to apply:**
- `scripts/run_screener.py` -- around the `load_config()` / `ScreenerConfig.model_validate()` calls (lines 76-88)
- `scripts/run_strategy.py` -- around the `load_config()` call in the `if screen:` block (line 86)

**Example:**
```python
# Source: Verified from existing codebase patterns
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from screener.config_loader import format_validation_errors

try:
    cfg = load_config(config)
except ValidationError as e:
    console = Console(stderr=True)
    error_text = format_validation_errors(e)
    panel = Panel(
        error_text,
        title="Configuration Error",
        border_style="red",
        expand=False,
    )
    console.print(panel)
    console.print(
        "[dim]See config/presets/ for valid examples "
        "or run-screener --preset conservative[/dim]"
    )
    raise typer.Exit(code=1)
```

**Key decisions:**
- Use `Console(stderr=True)` so errors go to stderr (standard practice)
- Use `border_style="red"` (errors are red; info panels in display.py use blue)
- Use `raise typer.Exit(code=1)` not `sys.exit(1)` since both CLIs use Typer
- The try/except scope in `run_screener.py` must wrap BOTH the `load_config()` path AND the `ScreenerConfig.model_validate()` path (the `if preset is not None` branch)

### Pattern 2: Monkeypatch load_dotenv for Test Isolation

**What:** The `load_dotenv(override=True)` call at module level in `config/credentials.py` reads the real `.env` file during `importlib.reload()`, overriding the monkeypatched environment variables. Fix by patching `load_dotenv` to a no-op before reloading.

**Root cause analysis (verified by running tests):**
1. Test calls `monkeypatch.setenv("FINNHUB_API_KEY", "test-key-abc123")`
2. Test calls `importlib.reload(creds)`
3. During reload, `load_dotenv(override=True)` runs, reads `.env`, and sets `FINNHUB_API_KEY` back to the real value
4. `os.getenv("FINNHUB_API_KEY")` returns the real key, not the test key

**Fix:**
```python
def test_finnhub_key_loaded(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key-abc123")
    import config.credentials as creds
    monkeypatch.setattr("config.credentials.load_dotenv", lambda **kwargs: None)
    importlib.reload(creds)
    assert creds.FINNHUB_API_KEY == "test-key-abc123"
```

**Alternative (also valid):** Patch at the `dotenv` module level:
```python
monkeypatch.setattr("dotenv.load_dotenv", lambda **kwargs: None)
```

The first approach (patching on the module being reloaded) is more targeted but has a subtlety: after `importlib.reload`, the monkeypatch target no longer exists in the reloaded module namespace. The safer approach is:

```python
def test_finnhub_key_loaded(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key-abc123")
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **kw: None)
    import config.credentials as creds
    importlib.reload(creds)
    assert creds.FINNHUB_API_KEY == "test-key-abc123"
```

This patches `dotenv.load_dotenv` at the source, so when `credentials.py` runs `from dotenv import load_dotenv` during reload, it picks up the patched version.

**Recommendation:** Patch `dotenv.load_dotenv` since the import `from dotenv import load_dotenv` in credentials.py creates a new binding during reload.

### Pattern 3: pyproject.toml Dependency Addition

**What:** Add three entries to the `[project.dependencies]` list.

**Current state:**
```toml
dependencies = [
    "python-dotenv",
    "pandas>=1.5",
    "numpy>=1.23",
    "pytz",
    "requests>=2.28",
    "alpaca-py",
    "finnhub-python",
    "rich>=14.0",
    "typer>=0.9.0",
]
```

**Target state (add 3 lines):**
```toml
dependencies = [
    "python-dotenv",
    "pandas>=1.5",
    "numpy>=1.23",
    "pytz",
    "requests>=2.28",
    "alpaca-py",
    "finnhub-python",
    "rich>=14.0",
    "typer>=0.9.0",
    "ta>=0.11",
    "pyyaml>=6.0",
    "pydantic>=2.0",
]
```

### Anti-Patterns to Avoid
- **Catching ValidationError inside config_loader.py:** User decision locks this at CLI entry points. The config_loader should continue to raise ValidationError.
- **Using sys.exit() in Typer commands:** Use `raise typer.Exit(code=1)` instead for proper Typer lifecycle.
- **Patching load_dotenv on the credentials module after reload:** The reload creates a fresh binding, making pre-reload patches ineffective. Patch on `dotenv.load_dotenv` instead.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Validation error formatting | Custom error parser | `format_validation_errors()` | Already exists in `screener/config_loader.py`, tested in Phase 1 |
| Rich error panels | Custom print formatting | `rich.panel.Panel` | Already used in `screener/display.py` for filter summaries |
| Module-level env isolation | Custom test fixtures | `monkeypatch.setattr` on `dotenv.load_dotenv` | Standard pytest pattern, established in Phase 1 |

## Common Pitfalls

### Pitfall 1: load_dotenv override=True Defeats Monkeypatch
**What goes wrong:** `monkeypatch.setenv()` sets the env var, but `importlib.reload()` triggers `load_dotenv(override=True)` which reads the real `.env` file and overwrites the monkeypatched value.
**Why it happens:** `override=True` tells dotenv to overwrite existing env vars with values from `.env`. During reload, the module's top-level `load_dotenv(override=True)` runs unconditionally.
**How to avoid:** Patch `dotenv.load_dotenv` to a no-op BEFORE calling `importlib.reload()`.
**Warning signs:** Tests pass when no `.env` file exists, fail when it does. Test assertions show real API keys instead of test values.

### Pitfall 2: Try/Except Scope in run_screener.py
**What goes wrong:** The `run_screener.py` has TWO code paths that can raise ValidationError -- the `if preset is not None` branch (line 86: `ScreenerConfig.model_validate(merged)`) and the `else` branch (line 88: `load_config(config)`). If the try/except only wraps one branch, the other still produces raw tracebacks.
**Why it happens:** The `--preset` override path constructs and validates the config differently from the default path.
**How to avoid:** The try/except must wrap the entire config-loading block (lines 76-88), covering both branches.
**Warning signs:** `run-screener --preset aggressive` with invalid YAML shows nice error, but `run-screener` with invalid YAML shows raw traceback (or vice versa).

### Pitfall 3: FinnhubAPIException Tests Are Already Fixed
**What goes wrong:** Spending time "fixing" test_finnhub_client.py when it already passes.
**Why it happens:** The deferred-items.md describes a historical issue. The tests already have `mock_finnhub.FinnhubAPIException = finnhub.FinnhubAPIException` on every relevant test.
**How to avoid:** Run `pytest tests/test_finnhub_client.py -v` to confirm -- all 21 tests pass. The deferred-items.md is stale.
**Warning signs:** N/A -- confirmed via test run on 2026-03-11.

### Pitfall 4: Missing Import for ValidationError in CLI Files
**What goes wrong:** Adding try/except for `ValidationError` but forgetting to import it from pydantic.
**Why it happens:** `ValidationError` is imported in `config_loader.py` but not in the CLI scripts.
**How to avoid:** Add `from pydantic import ValidationError` to both `scripts/run_screener.py` and `scripts/run_strategy.py`. Also need `from rich.console import Console` and `from rich.panel import Panel` in both.

## Code Examples

### Example 1: Config Error Display (run_screener.py)

```python
# Source: Verified pattern from screener/display.py (Panel usage) + config_loader.py (format_validation_errors)

from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from screener.config_loader import format_validation_errors

# Inside the run() function, wrap both config loading paths:
try:
    if preset is not None:
        preset_data = load_preset(preset.value)
        config_path = Path(config)
        if config_path.exists():
            with open(config_path) as f:
                user_config = yaml.safe_load(f) or {}
        else:
            user_config = {}
        user_config["preset"] = preset.value
        merged = deep_merge(preset_data, user_config)
        cfg = ScreenerConfig.model_validate(merged)
    else:
        cfg = load_config(config)
except ValidationError as e:
    console = Console(stderr=True)
    error_text = format_validation_errors(e)
    panel = Panel(
        error_text,
        title="Configuration Error",
        border_style="red",
        expand=False,
    )
    console.print(panel)
    console.print(
        "[dim]See config/presets/ for valid examples "
        "or run-screener --preset conservative[/dim]"
    )
    raise typer.Exit(code=1)
```

### Example 2: Config Error Display (run_strategy.py)

```python
# Source: Same pattern, applied to the --screen block

# Inside run(), within the `if screen:` block:
try:
    cfg = load_config()
except ValidationError as e:
    console = Console(stderr=True)
    error_text = format_validation_errors(e)
    panel = Panel(
        error_text,
        title="Configuration Error",
        border_style="red",
        expand=False,
    )
    console.print(panel)
    console.print(
        "[dim]See config/presets/ for valid examples "
        "or run-screener --preset conservative[/dim]"
    )
    raise typer.Exit(code=1)
```

### Example 3: Test Isolation Fix (test_credentials.py)

```python
# Source: Established monkeypatch + reload pattern from Phase 1 decisions

def test_finnhub_key_loaded(monkeypatch):
    """When FINNHUB_API_KEY is set in environment, the module-level variable holds the value."""
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key-abc123")
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **kw: None)
    import config.credentials as creds
    importlib.reload(creds)
    assert creds.FINNHUB_API_KEY == "test-key-abc123"


def test_finnhub_key_missing_is_none(monkeypatch):
    """When FINNHUB_API_KEY is not in environment, the module-level variable is None."""
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **kw: None)
    import config.credentials as creds
    importlib.reload(creds)
    assert creds.FINNHUB_API_KEY is None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw Pydantic tracebacks on invalid config | Human-readable Rich Panel with field errors | This phase | Users see actionable error messages instead of Python internals |
| Manual `pip install ta pyyaml pydantic` after `pip install -e .` | All deps declared in pyproject.toml | This phase | Fresh virtualenv setup works without manual intervention |
| Tests leak real `.env` values via load_dotenv | Monkeypatch load_dotenv to no-op before reload | This phase | Tests pass regardless of `.env` contents |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml (no `[tool.pytest]` section detected -- uses defaults) |
| Quick run command | `python -m pytest tests/test_credentials.py -x` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements --> Test Map

This phase has no formal requirement IDs, but success criteria map to verifiable tests:

| Success Criterion | Behavior | Test Type | Automated Command | File Exists? |
|-------------------|----------|-----------|-------------------|-------------|
| SC-1: pip install -e . | All deps install cleanly | smoke | `pip install -e . && python -c "import ta; import yaml; import pydantic"` | N/A (manual verification) |
| SC-2: Config error UX | ValidationError shows Rich Panel | unit | `python -m pytest tests/test_cli_screener.py -x -k "config_error"` | No -- Wave 0 |
| SC-3: Test isolation | Credential tests pass with real .env | unit | `python -m pytest tests/test_credentials.py -x` | Yes (needs fix) |
| SC-4: Stale cleanup | deferred-items.md removed | manual | `test ! -f .planning/phases/02-data-sources/deferred-items.md` | N/A |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_credentials.py tests/test_cli_screener.py tests/test_cli_strategy.py -x`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green (191 tests + new ones, 0 failures) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_cli_screener.py` -- add test for invalid config producing Rich Panel error (not traceback)
- [ ] `tests/test_cli_strategy.py` -- add test for invalid config with --screen producing Rich Panel error

*(Optional -- the CONTEXT.md does not explicitly require new tests for config error UX; the existing test infrastructure already exercises the CLI entry points. The planner should decide if new tests are needed based on the success criteria wording.)*

## Open Questions

1. **Should the error catch helper be extracted into a shared function?**
   - What we know: The same try/except + Panel pattern is needed in both run_screener.py and run_strategy.py
   - What's unclear: Whether to duplicate ~10 lines or extract a `_show_config_error(e: ValidationError)` helper
   - Recommendation: Extract a shared helper into `core/cli_common.py` (which already exists for shared CLI utilities). This avoids duplication and keeps the pattern consistent if more CLI entry points are added later.

2. **Should we also patch ALPACA credentials tests that use reload?**
   - What we know: Only `test_finnhub_key_loaded` and `test_finnhub_key_missing_is_none` fail. The Alpaca credential tests (`test_require_finnhub_key_returns_key`, `test_require_finnhub_key_raises_when_missing`) use `monkeypatch.setattr` directly on the module attribute (not reload), so they already work.
   - What's unclear: Nothing -- current test results confirm only 2 tests fail.
   - Recommendation: Fix only the 2 failing tests. The other 2 already pass.

## Sources

### Primary (HIGH confidence)
- **Direct codebase inspection:** pyproject.toml, config/credentials.py, screener/config_loader.py, scripts/run_screener.py, scripts/run_strategy.py, tests/test_credentials.py, tests/test_finnhub_client.py, screener/display.py
- **Test execution results:** `pytest tests/ -v` run on 2026-03-11 confirms exactly 2 failures (both in test_credentials.py), 189 passed
- **pip show output:** Confirmed installed versions of ta (0.11.0), PyYAML (6.0.3), pydantic (2.12.5)

### Secondary (MEDIUM confidence)
- Phase 1 decisions in STATE.md documenting the monkeypatch + reload pattern

### Tertiary (LOW confidence)
- None -- all findings are directly verified from the codebase and test execution

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified installed versions, confirmed missing from pyproject.toml
- Architecture: HIGH - all patterns verified from existing codebase code
- Pitfalls: HIGH - root causes confirmed by running tests and inspecting source
- Test isolation fix: HIGH - failure mode reproduced and root cause verified (load_dotenv override=True)

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable -- no external dependencies changing)