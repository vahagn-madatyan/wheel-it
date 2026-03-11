---
phase: 6
slug: packaging-cleanup
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pyproject.toml (no `[tool.pytest]` section — uses defaults) |
| **Quick run command** | `python -m pytest tests/test_credentials.py -x` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_credentials.py tests/test_cli_screener.py tests/test_cli_strategy.py -x`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | SC-1 (deps) | smoke | `pip install -e . && python -c "import ta; import yaml; import pydantic"` | N/A | ⬜ pending |
| 06-01-02 | 01 | 1 | SC-4 (cleanup) | manual | `test ! -f .planning/phases/02-data-sources/deferred-items.md` | N/A | ⬜ pending |
| 06-02-01 | 02 | 1 | SC-2 (config UX) | unit | `python -m pytest tests/test_cli_screener.py -x -k "config_error"` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 1 | SC-2 (config UX) | unit | `python -m pytest tests/test_cli_strategy.py -x -k "config_error"` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 1 | SC-3 (test isolation) | unit | `python -m pytest tests/test_credentials.py -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cli_screener.py` — add test for invalid config producing Rich Panel error (not traceback)
- [ ] `tests/test_cli_strategy.py` — add test for invalid config with --screen producing Rich Panel error

*Existing infrastructure covers SC-1 (smoke), SC-3 (existing tests need fix), and SC-4 (manual check).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| pip install -e . works | SC-1 | Requires clean venv | `uv venv /tmp/test-venv && source /tmp/test-venv/bin/activate && pip install -e . && python -c "import ta; import yaml; import pydantic"` |
| deferred-items.md removed | SC-4 | File deletion check | `test ! -f .planning/phases/02-data-sources/deferred-items.md && echo PASS` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
