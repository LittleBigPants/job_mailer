---
phase: 5
slug: sending-and-logging
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — testpaths=["tests"], addopts="-x" |
| **Quick run command** | `uv run pytest tests/test_sender.py tests/test_logger.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_sender.py tests/test_logger.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 0 | SEND-01 | unit | `uv run pytest tests/test_sender.py::test_send_success -x` | ❌ W0 | ⬜ pending |
| 5-01-02 | 01 | 0 | SEND-02 | unit | `uv run pytest tests/test_sender.py::test_rate_limit_continues -x` | ❌ W0 | ⬜ pending |
| 5-01-03 | 01 | 0 | SEND-02 | unit | `uv run pytest tests/test_sender.py::test_daily_quota_reraises -x` | ❌ W0 | ⬜ pending |
| 5-01-04 | 01 | 0 | SEND-02 | unit | `uv run pytest tests/test_sender.py::test_send_failed_non_429 -x` | ❌ W0 | ⬜ pending |
| 5-01-05 | 01 | 0 | LOG-01 | unit | `uv run pytest tests/test_logger.py::test_log_written_immediately -x` | ❌ W0 | ⬜ pending |
| 5-01-06 | 01 | 0 | LOG-01 | unit | `uv run pytest tests/test_logger.py::test_log_appends -x` | ❌ W0 | ⬜ pending |
| 5-01-07 | 01 | 0 | LOG-02 | unit | `uv run pytest tests/test_logger.py::test_log_fields -x` | ❌ W0 | ⬜ pending |
| 5-01-08 | 01 | 0 | LOG-02 | unit | `uv run pytest tests/test_logger.py::test_header_written_once -x` | ❌ W0 | ⬜ pending |
| 5-02-01 | 02 | 1 | SEND-03 | unit | `uv run pytest tests/test_cli.py::test_send_delay_called -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_sender.py` — stubs for SEND-01, SEND-02 (all error branches)
- [ ] `tests/test_logger.py` — stubs for LOG-01, LOG-02
- [ ] `models.py` update: `Status.RATE_LIMITED = "rate_limited"` must exist before RED test import works

*No new test infrastructure needed — pytest + unittest.mock covers all patterns; resend SDK calls mocked with `unittest.mock.patch`*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Terminal output format matches spec (`"  {company} — {email} — sent"`, `"  WARNING: ..."`, `"Done. X sent..."`) | SEND-01, SEND-02 | Output formatting checked by reading stdout; automated test would be brittle | Run `uv run python -m job_mailer` with test CSV and verify terminal output matches CONTEXT.md spec |
| `daily_quota_exceeded` prints correct error message and exits cleanly (no traceback) | SEND-02 | Requires Resend API returning the specific error; not easily mockable end-to-end | Mock `resend.Emails.send` to raise `RateLimitError` with `error_type="daily_quota_exceeded"`; verify exit code 1 and correct stderr message |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
