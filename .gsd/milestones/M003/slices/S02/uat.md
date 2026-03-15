# S02: Put Screener CLI + Strategy Integration — UAT

## Test Script

### 1. CLI help works
```bash
run-put-screener --help
```
**Expected:** Shows SYMBOLS, --buying-power, --preset, --config flags.

### 2. Strategy help works  
```bash
run-strategy --help
```
**Expected:** Shows all flags, exits 0.

### 3. All tests pass
```bash
python -m pytest tests/ -q
```
**Expected:** 425+ tests pass, 0 failures.

### 4. No legacy imports
```bash
grep "from core.execution" scripts/run_strategy.py
```
**Expected:** No output (zero matches).
