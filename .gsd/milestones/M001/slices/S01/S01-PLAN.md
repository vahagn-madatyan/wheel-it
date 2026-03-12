# S01: Foundation

**Goal:** Create the YAML config loading pipeline with preset profiles, Pydantic validation, and the ScreenedStock data model.
**Demo:** Create the YAML config loading pipeline with preset profiles, Pydantic validation, and the ScreenedStock data model.

## Must-Haves


## Tasks

- [x] **T01: 01-foundation 01** `est:5min`
  - Create the YAML config loading pipeline with preset profiles, Pydantic validation, and the ScreenedStock data model.

Purpose: Establish the configuration foundation so users can customize screening criteria through YAML files with preset profiles, and the system validates all input with clear error messages. Also define the ScreenedStock data model that later phases populate.
Output: Working config loader with 3 preset YAML files, Pydantic validation models, ScreenedStock dataclass, and comprehensive tests.
- [x] **T02: 01-foundation 02** `est:2min`
  - Add Finnhub API key loading to the existing credentials module with a hard-error helper function.

Purpose: Ensure the screener can access the Finnhub API key from .env with a clear error message if it's missing, following the existing credentials.py pattern.
Output: Extended credentials.py with FINNHUB_API_KEY and require_finnhub_key(), plus tests.

## Files Likely Touched

- `screener/__init__.py`
- `screener/config_loader.py`
- `config/presets/conservative.yaml`
- `config/presets/moderate.yaml`
- `config/presets/aggressive.yaml`
- `models/screened_stock.py`
- `tests/__init__.py`
- `tests/conftest.py`
- `tests/test_screener_config.py`
- `config/credentials.py`
- `tests/test_credentials.py`
