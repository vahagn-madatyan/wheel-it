---
estimated_steps: 4
estimated_files: 2
---

# T02: Update CLAUDE.md and README.md

**Slice:** S03 — Legacy Code Removal + Docs Update
**Milestone:** M003

## Description

Update project documentation to reflect the new architecture: removed modules, new modules, updated CLI commands.

## Steps

1. Read `CLAUDE.md` and identify sections referencing `core/strategy.py`, `core/execution.py`, `models/contract.py`, or obsolete config params.
2. Update `CLAUDE.md`:
   - Remove `core/execution.py` from Key Modules (replaced by `screener/put_screener.py` and `screener/call_screener.py`)
   - Remove `core/strategy.py` from Key Modules
   - Remove `models/contract.py` from Key Modules
   - Add `screener/put_screener.py` — `PutRecommendation` dataclass, `screen_puts()` for multi-symbol put screening with buying power pre-filter, `render_put_results_table()` for Rich display
   - Update `config/params.py` description to list only `MAX_RISK`, `DELTA_MIN`, `DELTA_MAX`
   - Update Flow description: `sell_puts()` → `screen_puts()`, `sell_calls()` → `screen_calls()`
   - Add `run-put-screener` to the CLI commands section
3. Update `README.md`: add `run-put-screener` usage example, update architecture description if present.
4. Verify no references to deleted modules remain in either doc.

## Must-Haves

- [ ] `CLAUDE.md` does not reference `core/strategy.py`, `core/execution.py`, or `models/contract.py` as existing modules
- [ ] `CLAUDE.md` documents `screener/put_screener.py`
- [ ] `CLAUDE.md` mentions `run-put-screener` CLI command
- [ ] `config/params.py` description lists only `MAX_RISK`, `DELTA_MIN`, `DELTA_MAX`

## Verification

- Read `CLAUDE.md` — no references to deleted modules
- `rg "core/strategy|core/execution|models/contract" CLAUDE.md README.md` — zero matches (or only historical context)

## Inputs

- Current `CLAUDE.md` and `README.md`
- Knowledge of all changes made in S01–S03

## Expected Output

- `CLAUDE.md` — accurately describes current architecture
- `README.md` — updated with new CLI and architecture
