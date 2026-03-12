---
estimated_steps: 4
estimated_files: 2
---

# T01: Merge scanning-improvements branch and validate test baseline

**Slice:** S07 — Pipeline Fix + Preset Overhaul
**Milestone:** M001

## Description

All S01–S06 screener code (860-line pipeline, 10 filter functions, 63 tests, 3 preset YAMLs, config loader, Finnhub client, display module) exists only on the `scanning-improvements` branch (106 commits ahead). The current `gsd/M001/S07` branch has only `.pyc` caches in `screener/` — no source files to edit. This task merges the branches and validates the existing test suite as a green baseline before any S07 changes begin.

## Steps

1. Run `git merge scanning-improvements --no-edit` to merge 106 commits into `gsd/M001/S07`. Expect clean merge since branches touch different files (docs vs screener code). If `pyproject.toml` or `.gitignore` conflict, accept the `scanning-improvements` version for code sections and keep both doc sections.
2. Verify key source files exist on disk: `screener/pipeline.py`, `screener/finnhub_client.py`, `screener/config_loader.py`, `config/presets/moderate.yaml`, `tests/test_pipeline.py`, `models/screened_stock.py`.
3. Activate the venv and install the package: `source .venv/bin/activate && uv pip install -e .` to ensure all dependencies from merged `pyproject.toml` are available.
4. Run `pytest tests/test_pipeline.py -v` and confirm all 63 test functions pass. Record the exact test count as the baseline for subsequent tasks.

## Must-Haves

- [ ] `scanning-improvements` branch merged into `gsd/M001/S07` without unresolved conflicts
- [ ] All screener source files (`screener/pipeline.py`, `screener/config_loader.py`, `screener/finnhub_client.py`, `screener/display.py`, `screener/market_data.py`) exist on disk
- [ ] All 3 preset YAML files exist: `config/presets/conservative.yaml`, `config/presets/moderate.yaml`, `config/presets/aggressive.yaml`
- [ ] `pytest tests/test_pipeline.py -v` passes all 63 tests (green baseline)

## Verification

- `ls screener/pipeline.py screener/finnhub_client.py config/presets/moderate.yaml tests/test_pipeline.py` — all exist
- `pytest tests/test_pipeline.py -v` — 63 passed, 0 failed
- `git log --oneline -3` — shows merge commit at HEAD

## Observability Impact

- Signals added/changed: None — merge only, no runtime changes
- How a future agent inspects this: `git log --oneline scanning-improvements..HEAD` shows merge commit
- Failure state exposed: None

## Inputs

- `scanning-improvements` branch — 106 commits of S01–S06 implementation
- `gsd/M001/S07` branch — current working branch with 2 commits (roadmap docs, research)

## Expected Output

- Working branch `gsd/M001/S07` with all screener source code, tests, and preset YAMLs available on disk
- Green test baseline: 63/63 tests passing
- Clean git history with merge commit
