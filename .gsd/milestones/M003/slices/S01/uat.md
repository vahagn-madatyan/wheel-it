# S01: Put Screener Module — UAT

## Prerequisites
- `pip install -e .` in an activated virtualenv

## Test Script

### 1. Verify tests pass
```bash
python -m pytest tests/test_put_screener.py -v
```
**Expected:** 50 tests pass, 0 failures.

### 2. Verify module is importable
```python
from screener.put_screener import PutRecommendation, screen_puts, render_put_results_table, compute_put_annualized_return
```
**Expected:** No import errors.

### 3. Verify annualized return math
```python
from screener.put_screener import compute_put_annualized_return
assert compute_put_annualized_return(1.50, 150.0, 30) == 12.17
assert compute_put_annualized_return(0, 150.0, 30) == 0.0
assert compute_put_annualized_return(1.50, 0, 30) is None
```
**Expected:** All assertions pass.

### 4. Verify full test suite unbroken
```bash
python -m pytest tests/ -q
```
**Expected:** 418+ tests pass, 0 failures.
