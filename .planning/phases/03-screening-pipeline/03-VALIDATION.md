---
phase: 03
slug: screening-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | None (defaults work; tests run from /tmp) |
| **Quick run command** | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/test_pipeline.py -x -q` |
| **Full suite command** | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd /tmp && python -m pytest tests/test_pipeline.py -x -q`
- **After every plan wave:** Run `cd /tmp && python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | FILT-01 | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestMarketCapFilter -x` | No — W0 | ⬜ pending |
| 03-01-01 | 01 | 1 | FILT-02 | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestDebtEquityFilter -x` | No — W0 | ⬜ pending |
| 03-01-01 | 01 | 1 | FILT-03 | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestNetMarginFilter -x` | No — W0 | ⬜ pending |
| 03-01-01 | 01 | 1 | FILT-04 | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestSalesGrowthFilter -x` | No — W0 | ⬜ pending |
| 03-01-01 | 01 | 1 | FILT-05 | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestPriceRangeFilter -x` | No — W0 | ⬜ pending |
| 03-01-01 | 01 | 1 | FILT-06 | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestVolumeFilter -x` | No — W0 | ⬜ pending |
| 03-01-01 | 01 | 1 | FILT-07 | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestRSIFilter -x` | No — W0 | ⬜ pending |
| 03-01-01 | 01 | 1 | FILT-08 | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestSMA200Filter -x` | No — W0 | ⬜ pending |
| 03-01-01 | 01 | 1 | FILT-09 | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestOptionableFilter -x` | No — W0 | ⬜ pending |
| 03-01-01 | 01 | 1 | FILT-10 | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestSectorFilter -x` | No — W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | SCOR-01 | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestScoring -x` | No — W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | SCOR-02 | unit | `cd /tmp && python -m pytest tests/test_pipeline.py::TestScoreSorting -x` | No — W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_pipeline.py` — stubs for FILT-01 through FILT-10, SCOR-01, SCOR-02
- [ ] No new framework install needed — pytest 9.0.2 already configured and working

*Existing infrastructure covers framework requirements.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
