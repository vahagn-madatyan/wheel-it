"""YAML config loading pipeline with preset profiles, deep merge, and Pydantic validation."""

import logging as stdlib_logging
from copy import deepcopy
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError, field_validator

logger = stdlib_logging.getLogger(__name__)

# Resolve the project root so preset paths work regardless of cwd
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PRESETS_DIR = _PROJECT_ROOT / "config" / "presets"


# ---------------------------------------------------------------------------
# Pydantic config models
# ---------------------------------------------------------------------------


class FundamentalsConfig(BaseModel):
    """Fundamental screening thresholds."""

    market_cap_min: int = 2_000_000_000
    debt_equity_max: float = 1.0
    net_margin_min: float = 0.0
    sales_growth_min: float = 5.0

    @field_validator("market_cap_min")
    @classmethod
    def market_cap_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("market_cap_min must be positive")
        return v

    @field_validator("debt_equity_max")
    @classmethod
    def debt_equity_reasonable(cls, v: float) -> float:
        if v < 0:
            raise ValueError("debt_equity_max must be >= 0")
        if v > 10:
            raise ValueError(f"debt_equity_max={v} is unusually high; typical range 0-5")
        return v


class TechnicalsConfig(BaseModel):
    """Technical screening thresholds."""

    price_min: float = 10.0
    price_max: float = 50.0
    avg_volume_min: int = 2_000_000
    rsi_max: float = 60.0
    above_sma200: bool = True
    hv_percentile_min: float = 30.0

    @field_validator("price_min")
    @classmethod
    def price_min_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("price_min must be positive")
        return v

    @field_validator("price_max")
    @classmethod
    def price_max_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("price_max must be positive")
        return v

    @field_validator("rsi_max")
    @classmethod
    def rsi_in_range(cls, v: float) -> float:
        if v < 0 or v > 100:
            raise ValueError("rsi_max must be between 0 and 100")
        return v


class EarningsConfig(BaseModel):
    """Earnings proximity filter thresholds."""

    earnings_exclusion_days: int = 14

    @field_validator("earnings_exclusion_days")
    @classmethod
    def earnings_days_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("earnings_exclusion_days must be >= 0")
        return v


class OptionsConfig(BaseModel):
    """Options screening flags."""

    optionable: bool = True


class SectorsConfig(BaseModel):
    """Sector inclusion/exclusion lists."""

    include: list[str] = []
    exclude: list[str] = []


class ScreenerConfig(BaseModel):
    """Top-level screener configuration with nested sections."""

    preset: str = "moderate"
    fundamentals: FundamentalsConfig = FundamentalsConfig()
    technicals: TechnicalsConfig = TechnicalsConfig()
    earnings: EarningsConfig = EarningsConfig()
    options: OptionsConfig = OptionsConfig()
    sectors: SectorsConfig = SectorsConfig()

    @field_validator("preset")
    @classmethod
    def valid_preset(cls, v: str) -> str:
        allowed = {"conservative", "moderate", "aggressive"}
        if v not in allowed:
            raise ValueError(
                f"preset must be one of {sorted(allowed)}, got '{v}'"
            )
        return v


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def load_preset(preset_name: str) -> dict:
    """Load a preset YAML file from config/presets/.

    Args:
        preset_name: One of 'conservative', 'moderate', 'aggressive'.

    Returns:
        Parsed YAML dict with all preset values.

    Raises:
        FileNotFoundError: If preset file does not exist.
    """
    preset_path = _PRESETS_DIR / f"{preset_name}.yaml"
    if not preset_path.exists():
        available = [p.stem for p in _PRESETS_DIR.glob("*.yaml")]
        raise FileNotFoundError(
            f"Unknown preset '{preset_name}'. "
            f"Available: {', '.join(sorted(available))}"
        )
    with open(preset_path) as f:
        return yaml.safe_load(f)


def deep_merge(base: dict, overrides: dict) -> dict:
    """Recursively merge overrides into base dict.

    When both base[key] and overrides[key] are dicts, recurse.
    Otherwise overrides[key] wins. Base is not mutated.

    Args:
        base: The base dictionary (e.g., preset values).
        overrides: User overrides to apply on top.

    Returns:
        New merged dictionary.
    """
    result = deepcopy(base)
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def load_config(config_path: str = "config/screener.yaml") -> ScreenerConfig:
    """Load, merge with preset, and validate screener config.

    If the config file does not exist, auto-generates a default with
    the moderate preset and logs a warning.

    Args:
        config_path: Path to the user's screener.yaml file.

    Returns:
        Validated ScreenerConfig instance.

    Raises:
        pydantic.ValidationError: If config values are invalid.
    """
    path = Path(config_path)

    if not path.exists():
        _generate_default_config(path)
        logger.warning(
            "No screener.yaml found at %s, generated default with moderate preset",
            path,
        )

    with open(path) as f:
        user_config = yaml.safe_load(f) or {}

    preset_name = user_config.get("preset", "moderate")

    # Validate preset name early via Pydantic so invalid presets produce
    # a ValidationError rather than a FileNotFoundError
    _valid_presets = {"conservative", "moderate", "aggressive"}
    if preset_name not in _valid_presets:
        # Trigger Pydantic validation to produce a proper ValidationError
        ScreenerConfig.model_validate({"preset": preset_name})

    preset_data = load_preset(preset_name)

    # Deep merge: preset is base, user config is overrides
    merged = deep_merge(preset_data, user_config)

    # Validate with Pydantic
    return ScreenerConfig.model_validate(merged)


def _generate_default_config(path: Path) -> None:
    """Auto-generate a default screener.yaml with moderate preset.

    Creates parent directories if needed and writes a commented YAML file.

    Args:
        path: Where to write the generated config file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    header = (
        "# Screener Configuration\n"
        "# ======================\n"
        "#\n"
        "# Select a preset profile as the base:\n"
        "#   conservative - tight fundamentals (large-cap, low debt)\n"
        "#   moderate     - Finviz baseline values (default)\n"
        "#   aggressive   - loose fundamentals (small-cap, higher debt OK)\n"
        "#\n"
        "# Override individual values below. Unspecified values\n"
        "# use the selected preset's defaults.\n"
        "#\n"
        "# Example overrides:\n"
        "#   fundamentals:\n"
        "#     market_cap_min: 5000000000\n"
        "#   technicals:\n"
        "#     price_max: 100\n"
        "#   sectors:\n"
        "#     exclude:\n"
        "#       - Utilities\n"
        "#       - Real Estate\n"
        "\n"
    )

    default_data = {"preset": "moderate"}

    with open(path, "w") as f:
        f.write(header)
        yaml.dump(default_data, f, default_flow_style=False)


def format_validation_errors(e: ValidationError) -> str:
    """Format Pydantic validation errors into human-readable messages.

    Args:
        e: A Pydantic ValidationError.

    Returns:
        Multi-line string with one line per error, formatted as:
        '  field.path: message'
    """
    lines = []
    for err in e.errors():
        field_path = ".".join(str(loc) for loc in err["loc"])
        msg = err["msg"]
        lines.append(f"  {field_path}: {msg}")
    return "\n".join(lines)
