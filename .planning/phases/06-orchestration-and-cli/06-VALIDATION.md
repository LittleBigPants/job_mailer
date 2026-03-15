---
phase: 6
slug: orchestration-and-cli
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_cli.py -x` |
| **Full suite command** | `uv run pytest -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_cli.py -x`
- **After every plan wave:** Run `uv run pytest -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 0 | SEND-04 | unit | `uv run pytest tests/test_cli.py::test_dry_run_does_not_call_send_email -x` | ❌ W0 | ⬜ pending |
| 6-01-02 | 01 | 0 | SEND-04 | unit | `uv run pytest tests/test_cli.py::test_dry_run_logs_dry_run_status -x` | ❌ W0 | ⬜ pending |
| 6-01-03 | 01 | 0 | SEND-04 | unit | `uv run pytest tests/test_cli.py::test_dry_run_terminal_output -x` | ❌ W0 | ⬜ pending |
| 6-01-04 | 01 | 0 | SEND-04 | unit | `uv run pytest tests/test_cli.py::test_dry_run_summary_line -x` | ❌ W0 | ⬜ pending |
| 6-01-05 | 01 | 0 | LOG-03 | unit | `uv run pytest tests/test_cli.py::test_idempotency_skips_sent_url -x` | ❌ W0 | ⬜ pending |
| 6-01-06 | 01 | 0 | LOG-03 | unit | `uv run pytest tests/test_cli.py::test_idempotency_no_send_for_skipped -x` | ❌ W0 | ⬜ pending |
| 6-01-07 | 01 | 0 | LOG-03 | unit | `uv run pytest tests/test_cli.py::test_within_run_dedup -x` | ❌ W0 | ⬜ pending |
| 6-01-08 | 01 | 0 | LOG-03 | unit | `uv run pytest tests/test_cli.py::test_dry_run_respects_idempotency -x` | ❌ W0 | ⬜ pending |
| 6-01-09 | 01 | 0 | SEND-04 | unit | `uv run pytest tests/test_cli.py::test_cli_delay_flag_overrides_profile -x` | ❌ W0 | ⬜ pending |
| 6-01-10 | 01 | 0 | SEND-04 | unit | `uv run pytest tests/test_cli.py::test_cli_delay_default_is_2 -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cli.py` — append 10 test stubs for SEND-04 and LOG-03 (file exists, stubs needed)

*No new framework install needed — pytest is already installed.*

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
