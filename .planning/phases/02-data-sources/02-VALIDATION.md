---
phase: 02
slug: data-sources
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already configured, 30 tests passing from Phase 1) |
| **Config file** | `tests/conftest.py` (exists with fixtures) |
| **Quick run command** | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/ -x -q` |
| **Full suite command** | `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/ -v` |
| **Estimated runtime** | ~2 seconds |

Note: Tests run from `/tmp` to avoid the project's `logging/` package shadowing Python's stdlib `logging` during pytest import.

---

## Sampling Rate

- **After every task commit:** Run `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/ -x -q`
- **After every plan wave:** Run `cd /tmp && python -m pytest /Users/djbeatbug/RoadToMillion/wheeely/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | SAFE-02 | unit | `cd /tmp && python -m pytest .../tests/test_finnhub_client.py -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | SAFE-04 | unit | `cd /tmp && python -m pytest .../tests/test_finnhub_client.py -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | N/A | unit | `cd /tmp && python -m pytest .../tests/test_market_data.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_finnhub_client.py` — stubs for SAFE-02 (rate limiting, 429 retry) and SAFE-04 (fallback chains, empty responses)
- [ ] `tests/test_market_data.py` — stubs for RSI/SMA computation, insufficient bar handling, multi-symbol batching

*Existing infrastructure covers test framework and conftest fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 200+ symbols without 429 errors | SAFE-02 | Requires live Finnhub API key and real rate limit | Run `run-screener` with 200+ symbol universe and monitor for 429 errors |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
