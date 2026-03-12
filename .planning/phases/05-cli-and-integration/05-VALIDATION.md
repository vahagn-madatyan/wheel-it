---
phase: 5
slug: cli-and-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already in use) |
| **Config file** | none — no pytest.ini or pyproject.toml [tool.pytest] section |
| **Quick run command** | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/ -x -q` |
| **Full suite command** | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/ -x -q`
- **After every plan wave:** Run `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | CLI-01 | integration | `cd /tmp && python -m pytest tests/test_cli_screener.py -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | CLI-04 | integration | `cd /tmp && python -m pytest tests/test_cli_screener.py::test_default_no_file_writes -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | CLI-03 | unit | `cd /tmp && python -m pytest tests/test_export.py -x` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 1 | OUTP-03 | unit | `cd /tmp && python -m pytest tests/test_export.py::test_export_writes_file -x` | ❌ W0 | ⬜ pending |
| 05-01-05 | 01 | 1 | SAFE-03 | unit | `cd /tmp && python -m pytest tests/test_export.py::test_protected_symbols_kept -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 1 | CLI-02 | integration | `cd /tmp && python -m pytest tests/test_cli_strategy.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cli_screener.py` — stubs for CLI-01, CLI-04 (Typer CliRunner tests for run-screener)
- [ ] `tests/test_cli_strategy.py` — stubs for CLI-02 (Typer CliRunner tests for run-strategy --screen)
- [ ] `tests/test_export.py` — stubs for CLI-03, OUTP-03, SAFE-03 (symbol export with position protection)
- [ ] `typer` package install: `uv pip install typer` — required for all new code

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | — | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
