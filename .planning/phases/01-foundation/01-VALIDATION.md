---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-07
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `python -m pytest tests/test_screener_config.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_screener_config.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | CONF-01 | unit | `python -m pytest tests/test_screener_config.py::test_load_yaml -x` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | CONF-02 | unit | `python -m pytest tests/test_screener_config.py::test_presets -x` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | CONF-03 | unit | `python -m pytest tests/test_screener_config.py::test_deep_merge -x` | ❌ W0 | ⬜ pending |
| 01-01-04 | 01 | 1 | CONF-04 | unit | `python -m pytest tests/test_screener_config.py::test_validation_errors -x` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | SAFE-01 | unit | `python -m pytest tests/test_screener_config.py::test_finnhub_key -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_screener_config.py` — stubs for CONF-01, CONF-02, CONF-03, CONF-04, SAFE-01
- [ ] `tests/conftest.py` — shared fixtures (tmp config dirs, sample YAML)
- [ ] `uv pip install pytest` — install test framework

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Auto-generated screener.yaml is readable | CONF-01 | File readability is subjective | Open generated file, verify YAML is well-formatted with comments |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
