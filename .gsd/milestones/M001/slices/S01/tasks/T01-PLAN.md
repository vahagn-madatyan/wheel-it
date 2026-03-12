# T01: 01-foundation 01

**Slice:** S01 — **Milestone:** M001

## Description

Create the YAML config loading pipeline with preset profiles, Pydantic validation, and the ScreenedStock data model.

Purpose: Establish the configuration foundation so users can customize screening criteria through YAML files with preset profiles, and the system validates all input with clear error messages. Also define the ScreenedStock data model that later phases populate.
Output: Working config loader with 3 preset YAML files, Pydantic validation models, ScreenedStock dataclass, and comprehensive tests.

## Must-Haves

- [ ] "User can create a screener.yaml with filter thresholds and the system loads it without error"
- [ ] "User can select a preset profile (conservative, moderate, aggressive) and see different thresholds applied"
- [ ] "User can override individual preset values in screener.yaml and the overrides take effect without clobbering other preset values"
- [ ] "User receives clear, actionable error messages when screener.yaml contains invalid values"
- [ ] "Missing screener.yaml auto-generates with moderate preset and logs a warning"

## Files

- `screener/__init__.py`
- `screener/config_loader.py`
- `config/presets/conservative.yaml`
- `config/presets/moderate.yaml`
- `config/presets/aggressive.yaml`
- `models/screened_stock.py`
- `tests/__init__.py`
- `tests/conftest.py`
- `tests/test_screener_config.py`
