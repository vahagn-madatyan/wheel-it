---
phase: 4
slug: output-and-display
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via `python -m pytest`) |
| **Config file** | none (default discovery) |
| **Quick run command** | `python -m pytest tests/test_display.py -x` |
| **Full suite command** | `python -m pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_display.py -x`
- **After every plan wave:** Run `python -m pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | OUTP-01 | unit | `python -m pytest tests/test_display.py::TestFormatters -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | OUTP-01 | unit | `python -m pytest tests/test_display.py::TestRenderResultsTable -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | OUTP-02 | unit | `python -m pytest tests/test_display.py::TestRenderStageSummary -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | OUTP-02 | unit | `python -m pytest tests/test_display.py::TestRenderFilterBreakdown -x` | ❌ W0 | ⬜ pending |
| 04-01-05 | 01 | 1 | OUTP-04 | unit | `python -m pytest tests/test_display.py::TestProgressCallback -x` | ❌ W0 | ⬜ pending |
| 04-01-06 | 01 | 1 | OUTP-04 | unit | `python -m pytest tests/test_pipeline.py::TestRunPipelineProgress -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_display.py` — stubs for OUTP-01, OUTP-02, OUTP-04 display functions
- [ ] `rich` library install — `uv pip install rich` (not currently in dependencies)
- [ ] Test strategy: Use `Console(file=StringIO(), width=120)` to capture output for assertions

*Existing `tests/` directory and pytest infrastructure from Phase 1-3 covers framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Color-coded scores visible in terminal | OUTP-01 | Colors only render in real terminal | Run screener, visually verify green/yellow/red scores |
| Progress bar updates smoothly | OUTP-04 | Requires real terminal for visual verification | Run screener with live API, watch progress bars |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
