---
phase: 1
slug: scaffolding
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (latest) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — Wave 0 installs |
| **Quick run command** | `pytest tests/test_config.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_config.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | INFRA-02 | unit | `pytest tests/test_config.py::test_check_env_missing_key -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | INFRA-02 | unit | `pytest tests/test_config.py::test_check_env_all_present -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | INFRA-02 | unit | `pytest tests/test_config.py::test_check_env_names_missing_key -x` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | INFRA-03 | unit | `pytest tests/test_config.py::test_load_profile_schema -x` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 1 | INFRA-03 | unit | `pytest tests/test_config.py::test_load_profile_missing_file -x` | ❌ W0 | ⬜ pending |
| 1-01-06 | 01 | 1 | INFRA-02 | smoke | `git status --short \| grep -v "^?" \| grep "\.env"` returns empty | N/A | ⬜ pending |
| 1-01-07 | 01 | 1 | INFRA-01 | smoke | `grep -c "SPF\|DKIM\|DMARC" README.md` returns >= 3 | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_config.py` — stubs for INFRA-02 (check_env) and INFRA-03 (load_profile)
- [ ] `tests/conftest.py` — shared fixtures (tmp_path, monkeypatch for env vars)
- [ ] pytest installed via `pyproject.toml` `[project.optional-dependencies]` dev group

*Wave 0 must be created before any implementation tasks run.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `.env` absent from git tracking | INFRA-02 | Git state cannot be asserted in a unit test | Run `git status --short \| grep -v "^?" \| grep "\.env"` — output must be empty |
| README DNS section readable | INFRA-01 | Content quality is human-judged | Open README.md, read DNS section — verify SPF/DKIM/DMARC records are explicit, not just mentioned |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
