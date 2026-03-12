# Phase 1: Foundation - Research

**Researched:** 2026-03-07
**Domain:** YAML configuration, Pydantic validation, data modeling, environment variable management
**Confidence:** HIGH

## Summary

Phase 1 establishes the configuration and data model foundation for the stock screener. The work involves four distinct areas: (1) YAML-based config loading with preset profiles stored in `config/presets/`, (2) Pydantic v2 validation models for config with clear error messages, (3) the `ScreenedStock` dataclass with progressive build pattern, and (4) Finnhub API key loading via `.env`.

All libraries needed are either already installed (Pydantic via alpaca-py, python-dotenv) or require only a simple `uv pip install` (PyYAML). The existing codebase provides strong patterns to follow: `config/credentials.py` for env var loading, `models/contract.py` for dataclass design with multiple constructors and Optional fields. No API calls or filtering logic belong in this phase.

**Primary recommendation:** Use Pydantic v2 `BaseModel` for config validation (already installed), PyYAML for parsing, standard `@dataclass` for ScreenedStock (matching existing project pattern), and extend `config/credentials.py` pattern for Finnhub key.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Finviz reference values are the **moderate** preset baseline
- Conservative is tighter on fundamentals, aggressive is looser
- **Technical filters are constant across all presets**: price $10-$50, avg volume >2M, RSI <60, price >SMA200
- Only fundamental filters vary by preset: debt/equity, net margin, sales growth, market cap thresholds
- Config file lives at `config/screener.yaml`
- `preset:` field at top selects the base profile (conservative, moderate, aggressive)
- Filters grouped by data source: `fundamentals:`, `technicals:`, `options:`, `sectors:`
- **Deep merge**: User overrides only specified fields; all other values come from the selected preset
- Preset YAML files stored in `config/presets/` directory
- **ScreenedStock full data model**: Carry all fetched data plus raw responses for debugging
- **Track filter results**: Each stock records pass/fail per filter
- **Progressive build pattern**: Start with symbol, add data progressively, fields Optional until populated
- **Missing screener.yaml**: Auto-generate `config/screener.yaml` with moderate preset on first run
- **Partial config**: Fill missing fields from preset, log warning per fallback
- **Missing FINNHUB_API_KEY**: Hard error with clear instructions
- **Invalid config values**: Pydantic validation with clear, actionable error messages

### Claude's Discretion
- Specific conservative and aggressive fundamental threshold values
- Pydantic model field naming conventions
- Internal structure of preset YAML files
- How to handle the `logging/` package shadow issue

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONF-01 | User can define screening filter thresholds in a YAML config file (config/screener.yaml) | PyYAML parsing + deep merge pattern + preset loading architecture |
| CONF-02 | Screener ships with preset profiles: conservative, moderate, aggressive (config/presets/) | Preset YAML file structure + recommended threshold values |
| CONF-03 | User can override individual preset values with custom values in screener.yaml | Deep merge implementation pattern with Pydantic model defaults |
| CONF-04 | Config is validated via Pydantic models with clear error messages for invalid values | Pydantic v2 BaseModel with validators + custom error formatting |
| SAFE-01 | Finnhub API key is loaded from .env file (FINNHUB_API_KEY) | Existing credentials.py pattern extension |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyYAML | 6.0.x | Parse YAML config files | Uncontested Python YAML standard; lightweight |
| Pydantic | 2.x | Config validation with typed models | Already installed via alpaca-py; v2 provides `model_validate`, field validators, clear errors |
| python-dotenv | (installed) | Load FINNHUB_API_KEY from .env | Already used in project for Alpaca keys |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dataclasses | stdlib | ScreenedStock model | Matches existing Contract pattern; no new dependency |
| pathlib | stdlib | File path handling for config/presets | Cleaner than os.path for config directory traversal |
| copy | stdlib | `copy.deepcopy` for preset merging | Safe dict deep copy before overlay |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyYAML | StrictYAML | Stricter parsing but redundant with Pydantic validation layer |
| Pydantic BaseModel | dataclass + manual validation | More code, worse error messages, no `model_validate` |
| dataclass (ScreenedStock) | Pydantic BaseModel | Pydantic adds overhead for a data carrier; dataclass matches existing Contract pattern |

**Installation:**
```bash
uv pip install pyyaml
```
(Pydantic and python-dotenv are already installed.)

## Architecture Patterns

### Recommended Project Structure
```
config/
  screener.yaml           # User config (auto-generated if missing)
  presets/
    conservative.yaml     # Tight fundamentals
    moderate.yaml         # Finviz baseline values
    aggressive.yaml       # Loose fundamentals
  credentials.py          # Existing -- extend for FINNHUB_API_KEY
  params.py               # Existing -- unchanged
  symbol_list.txt         # Existing -- unchanged
models/
  contract.py             # Existing -- unchanged
  screened_stock.py       # NEW: ScreenedStock dataclass
screener/
  config_loader.py        # NEW: YAML loading, preset merging, validation
  __init__.py
```

### Pattern 1: Config Loading Chain
**What:** YAML file -> PyYAML parse -> merge with preset -> Pydantic validate -> typed config object
**When to use:** Every time the screener starts up
**Example:**
```python
import yaml
from pathlib import Path
from pydantic import BaseModel, field_validator, ValidationError
from copy import deepcopy

def load_preset(preset_name: str) -> dict:
    """Load a preset YAML file from config/presets/."""
    preset_path = Path("config/presets") / f"{preset_name}.yaml"
    if not preset_path.exists():
        raise FileNotFoundError(
            f"Unknown preset '{preset_name}'. "
            f"Available: conservative, moderate, aggressive"
        )
    with open(preset_path) as f:
        return yaml.safe_load(f)

def deep_merge(base: dict, overrides: dict) -> dict:
    """Recursively merge overrides into base dict."""
    result = deepcopy(base)
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def load_config(config_path: str = "config/screener.yaml") -> "ScreenerConfig":
    """Load, merge, validate config. Auto-generate if missing."""
    path = Path(config_path)
    if not path.exists():
        _generate_default_config(path)
        # log warning: "No screener.yaml found, generated default with moderate preset"

    with open(path) as f:
        user_config = yaml.safe_load(f) or {}

    preset_name = user_config.get("preset", "moderate")
    preset_data = load_preset(preset_name)

    # Deep merge: preset is base, user values override
    merged = deep_merge(preset_data, user_config)

    # Validate with Pydantic
    return ScreenerConfig.model_validate(merged)
```

### Pattern 2: Pydantic Config Model with Grouped Sections
**What:** Nested Pydantic models matching the YAML structure
**When to use:** Config validation
**Example:**
```python
from pydantic import BaseModel, field_validator

class FundamentalsConfig(BaseModel):
    market_cap_min: int = 2_000_000_000
    debt_equity_max: float = 1.0
    net_margin_min: float = 0.0
    sales_growth_min: float = 5.0

    @field_validator("debt_equity_max")
    @classmethod
    def debt_equity_reasonable(cls, v):
        if v < 0:
            raise ValueError("debt_equity_max must be >= 0")
        if v > 10:
            raise ValueError(f"debt_equity_max={v} is unusually high; typical range 0-5")
        return v

class TechnicalsConfig(BaseModel):
    price_min: float = 10.0
    price_max: float = 50.0
    avg_volume_min: int = 2_000_000
    rsi_max: float = 60.0
    above_sma200: bool = True

    @field_validator("price_min")
    @classmethod
    def price_min_positive(cls, v):
        if v <= 0:
            raise ValueError("price_min must be positive")
        return v

class OptionsConfig(BaseModel):
    optionable: bool = True

class SectorsConfig(BaseModel):
    include: list[str] = []
    exclude: list[str] = []

class ScreenerConfig(BaseModel):
    preset: str = "moderate"
    fundamentals: FundamentalsConfig = FundamentalsConfig()
    technicals: TechnicalsConfig = TechnicalsConfig()
    options: OptionsConfig = OptionsConfig()
    sectors: SectorsConfig = SectorsConfig()

    @field_validator("preset")
    @classmethod
    def valid_preset(cls, v):
        allowed = {"conservative", "moderate", "aggressive"}
        if v not in allowed:
            raise ValueError(f"preset must be one of {allowed}, got '{v}'")
        return v
```

### Pattern 3: ScreenedStock Progressive Build
**What:** Dataclass with Optional fields, populated progressively as data sources are queried
**When to use:** Building stock data through the screening pipeline (Phase 2+), but model defined now
**Example:**
```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class FilterResult:
    """Pass/fail for a single filter with reason."""
    filter_name: str
    passed: bool
    actual_value: Optional[float] = None
    threshold: Optional[float] = None
    reason: str = ""

@dataclass
class ScreenedStock:
    symbol: str

    # Alpaca market data (Phase 2)
    price: Optional[float] = None
    avg_volume: Optional[float] = None

    # Finnhub fundamental data (Phase 2)
    market_cap: Optional[float] = None
    debt_equity: Optional[float] = None
    net_margin: Optional[float] = None
    sales_growth: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None

    # Technical indicators (Phase 3)
    rsi_14: Optional[float] = None
    sma_200: Optional[float] = None
    above_sma200: Optional[bool] = None

    # Options data (Phase 3)
    is_optionable: Optional[bool] = None

    # Scoring (Phase 3)
    score: Optional[float] = None

    # Filter tracking (Phase 4 output)
    filter_results: list[FilterResult] = field(default_factory=list)

    # Raw API responses for debugging
    raw_finnhub_profile: Optional[dict] = None
    raw_finnhub_metrics: Optional[dict] = None
    raw_alpaca_bars: Optional[dict] = None

    @classmethod
    def from_symbol(cls, symbol: str) -> "ScreenedStock":
        return cls(symbol=symbol.upper())

    @property
    def passed_all_filters(self) -> bool:
        if not self.filter_results:
            return False
        return all(r.passed for r in self.filter_results)

    @property
    def failed_filters(self) -> list[FilterResult]:
        return [r for r in self.filter_results if not r.passed]
```

### Pattern 4: Finnhub API Key Loading
**What:** Extend existing credentials.py pattern
**When to use:** Add FINNHUB_API_KEY alongside existing Alpaca keys
**Example:**
```python
# In config/credentials.py -- add to existing file
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

def require_finnhub_key() -> str:
    """Return Finnhub key or raise with actionable message."""
    if not FINNHUB_API_KEY:
        raise EnvironmentError(
            "FINNHUB_API_KEY not found in .env. "
            "Get a free key at https://finnhub.io/register"
        )
    return FINNHUB_API_KEY
```

### Anti-Patterns to Avoid
- **Don't validate in YAML parsing**: Let PyYAML just parse; let Pydantic handle all validation. Mixing validation layers creates confusion.
- **Don't use `yaml.load()` (unsafe)**: Always use `yaml.safe_load()` to prevent arbitrary code execution.
- **Don't flatten the config structure**: Keep the grouped structure (`fundamentals:`, `technicals:`, etc.) -- it matches the data sources and makes partial overrides intuitive.
- **Don't use Pydantic for ScreenedStock**: The existing project uses `@dataclass` for data carriers (see `Contract`). Pydantic adds serialization overhead not needed for an in-memory pipeline object.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML parsing | Custom parser | `yaml.safe_load()` | Edge cases in YAML spec are numerous |
| Config validation | Manual if/else chains | Pydantic `BaseModel` with `field_validator` | Type coercion, nested validation, error formatting all built-in |
| Deep dict merge | Simple `dict.update()` | Recursive `deep_merge()` function | `dict.update()` replaces nested dicts entirely instead of merging |
| Error formatting | Raw Pydantic errors | `ValidationError.errors()` with custom formatter | Raw Pydantic errors reference model internals; users need field names and human-readable messages |

**Key insight:** The validation chain (YAML -> merge -> Pydantic) is simple but the merge step is where bugs hide. A proper recursive deep merge is ~10 lines but must handle the case where a user provides a partial nested dict (e.g., only `fundamentals.market_cap_min`) without clobbering the rest of the preset's `fundamentals` section.

## Common Pitfalls

### Pitfall 1: yaml.safe_load Returns None for Empty Files
**What goes wrong:** If `screener.yaml` exists but is empty, `yaml.safe_load()` returns `None`, not `{}`.
**Why it happens:** YAML spec says empty document is null.
**How to avoid:** Always do `user_config = yaml.safe_load(f) or {}` after parsing.
**Warning signs:** `TypeError: argument of type 'NoneType' is not iterable` when accessing config.

### Pitfall 2: dict.update() Doesn't Deep Merge
**What goes wrong:** User overrides `fundamentals.market_cap_min: 5_000_000_000` but all other fundamental values from the preset are lost.
**Why it happens:** Python's `dict.update()` replaces entire nested dicts.
**How to avoid:** Use recursive deep merge function. Test with partial nested overrides.
**Warning signs:** Preset values disappearing when user overrides a single nested field.

### Pitfall 3: Pydantic v2 API Differences from v1
**What goes wrong:** Using `.dict()`, `@validator`, or `Config` class (all v1 patterns).
**Why it happens:** Many online examples still show Pydantic v1 syntax.
**How to avoid:** Use v2 API: `.model_dump()`, `@field_validator`, `model_config = ConfigDict(...)`.
**Warning signs:** `DeprecationWarning` or `AttributeError` on model methods.

### Pitfall 4: Logging Package Shadow
**What goes wrong:** The project's `logging/` package shadows Python's stdlib `logging`. If the screener module imports `logging` at the top level, it gets the project's package, not stdlib.
**Why it happens:** Python's import resolution checks local packages first.
**How to avoid:** For stdlib logging in screener modules, import explicitly: `import logging as stdlib_logging` or use the project's existing `from logging.logger_setup import setup_logger` pattern. Test imports from project root.
**Warning signs:** `AttributeError: module 'logging' has no attribute 'getLogger'`.

### Pitfall 5: YAML Numeric Underscores
**What goes wrong:** YAML 1.1 (PyYAML default) may not parse `2_000_000_000` as an integer.
**Why it happens:** Underscore-separated numbers are a YAML 1.1 feature but behavior varies by parser.
**How to avoid:** Test that PyYAML correctly parses underscore-separated integers. If not, use plain numbers (2000000000) in YAML files and document the format.
**Warning signs:** Config values parsed as strings instead of integers.

### Pitfall 6: Auto-Generated Config File Permissions
**What goes wrong:** Auto-generating `screener.yaml` on first run may fail if `config/` directory doesn't exist or has wrong permissions.
**Why it happens:** Assumes directory structure exists.
**How to avoid:** Use `Path.mkdir(parents=True, exist_ok=True)` before writing. The `config/` directory already exists in this project, but `config/presets/` is new.
**Warning signs:** `FileNotFoundError` on first run.

## Preset Threshold Values (Claude's Discretion)

Based on wheel strategy best practices -- conservative favors capital preservation, aggressive favors broader universe for premium opportunities.

### Recommended Fundamental Thresholds by Preset

| Filter | Conservative | Moderate (Finviz baseline) | Aggressive |
|--------|-------------|---------------------------|------------|
| market_cap_min | $10B (large-cap+) | $2B (mid-cap+) | $500M (small-cap+) |
| debt_equity_max | 0.5 | 1.0 | 2.0 |
| net_margin_min | 10% | 0% (positive) | -5% (slight loss OK) |
| sales_growth_min | 10% | 5% | 0% (flat OK) |

### Technical Thresholds (Constant Across All Presets)

| Filter | Value | Rationale |
|--------|-------|-----------|
| price_min | $10 | Avoid penny stocks; options have poor liquidity below $10 |
| price_max | $50 | Capital efficiency for cash-secured puts ($5,000 max per contract) |
| avg_volume_min | 2,000,000 | Ensures options liquidity |
| rsi_max | 60 | Avoid overbought stocks (selling puts on dips is ideal) |
| above_sma200 | true | Long-term uptrend confirmation |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (to be added) |
| Config file | none -- see Wave 0 |
| Quick run command | `pytest tests/test_config_loader.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONF-01 | Load screener.yaml with filter thresholds | unit | `pytest tests/test_config_loader.py::test_load_valid_config -x` | No -- Wave 0 |
| CONF-02 | Preset profiles load with correct values | unit | `pytest tests/test_config_loader.py::test_preset_loading -x` | No -- Wave 0 |
| CONF-03 | User overrides merge correctly over preset | unit | `pytest tests/test_config_loader.py::test_deep_merge_overrides -x` | No -- Wave 0 |
| CONF-04 | Invalid config produces clear error messages | unit | `pytest tests/test_config_loader.py::test_validation_errors -x` | No -- Wave 0 |
| SAFE-01 | Finnhub key loaded from .env, hard error if missing | unit | `pytest tests/test_credentials.py::test_finnhub_key_required -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_config_loader.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/` directory -- does not exist yet
- [ ] `tests/test_config_loader.py` -- covers CONF-01, CONF-02, CONF-03, CONF-04
- [ ] `tests/test_credentials.py` -- covers SAFE-01
- [ ] `tests/conftest.py` -- shared fixtures (temp config files, mock .env)
- [ ] pytest install: `uv pip install pytest` -- not currently a dependency
- [ ] `pytest.ini` or `pyproject.toml [tool.pytest]` -- configure test discovery to avoid `logging/` shadow issues

## Sources

### Primary (HIGH confidence)
- Existing codebase: `config/credentials.py` -- env var loading pattern verified
- Existing codebase: `models/contract.py` -- dataclass with Optional fields and multiple constructors verified
- Existing codebase: `pyproject.toml` -- current dependencies confirmed (Pydantic via alpaca-py, python-dotenv, pandas, numpy)
- `.planning/research/STACK.md` -- stack decisions already researched and documented

### Secondary (MEDIUM confidence)
- Pydantic v2 API: `BaseModel`, `field_validator`, `model_validate`, `ConfigDict` -- based on training data, Pydantic v2 has been stable since mid-2023
- PyYAML `safe_load` behavior with empty files and underscore numerics -- based on training data

### Tertiary (LOW confidence)
- Specific preset threshold values (conservative/aggressive) -- based on general wheel strategy knowledge; may need tuning after live API data is available

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries confirmed installed or trivially installable, patterns verified in codebase
- Architecture: HIGH -- follows existing project patterns (credentials.py, Contract dataclass), CONTEXT.md provides detailed structure
- Pitfalls: HIGH -- logging shadow is documented in CLAUDE.md, YAML/Pydantic pitfalls are well-known
- Preset values: MEDIUM -- reasonable defaults based on wheel strategy practices, but real-world tuning expected

**Research date:** 2026-03-07
**Valid until:** 2026-04-07 (stable domain, no fast-moving dependencies)