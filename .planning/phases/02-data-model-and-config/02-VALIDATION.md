---
phase: 2
slug: data-model-and-config
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (latest, already installed) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — exists with `testpaths = ["tests"]` and `addopts = "-x"` |
| **Quick run command** | `pytest tests/test_models.py tests/test_cli.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_models.py -x` (after models.py) or `pytest tests/test_config.py -x` (after config.py) or `pytest tests/test_cli.py -x` (after __main__.py)
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 0 | INPUT-01 | unit | `pytest tests/test_models.py -x` | ❌ W0 | ⬜ pending |
| 2-01-02 | 01 | 0 | INPUT-01 | unit | `pytest tests/test_config.py -x` | ❌ W0 | ⬜ pending |
| 2-01-03 | 01 | 0 | INPUT-01 | integration | `pytest tests/test_cli.py -x` | ❌ W0 | ⬜ pending |
| 2-02-01 | 02 | 1 | INPUT-01 | unit | `pytest tests/test_models.py::test_company_record_defaults -x` | ✅ W0 | ⬜ pending |
| 2-02-02 | 02 | 1 | INPUT-01 | unit | `pytest tests/test_models.py::test_company_record_fields -x` | ✅ W0 | ⬜ pending |
| 2-02-03 | 02 | 1 | INPUT-01 | unit | `pytest tests/test_models.py::test_status_enum_values -x` | ✅ W0 | ⬜ pending |
| 2-03-01 | 03 | 1 | INPUT-01 | unit | `pytest tests/test_config.py::test_validate_profile_missing_field -x` | ✅ W0 | ⬜ pending |
| 2-03-02 | 03 | 1 | INPUT-01 | unit | `pytest tests/test_config.py::test_validate_profile_all_present -x` | ✅ W0 | ⬜ pending |
| 2-04-01 | 04 | 1 | INPUT-01 | integration | `pytest tests/test_cli.py::test_cli_input_exits_clean -x` | ✅ W0 | ⬜ pending |
| 2-04-02 | 04 | 1 | INPUT-01 | unit | `pytest tests/test_cli.py::test_cli_missing_input_flag -x` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_models.py` — stubs for CompanyRecord and Status enum (INPUT-01)
- [ ] `tests/test_cli.py` — stubs for `--input` argument and exit-clean behavior (INPUT-01)
- [ ] Extend `tests/test_config.py` — stubs for `validate_profile()` missing field and all-present cases (INPUT-01)

*Existing `tests/conftest.py` from Phase 1 is extended, not replaced. `tests/test_config.py` already exists.*

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
