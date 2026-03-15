---
phase: 4
slug: llm-generation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_generator.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_generator.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 0 | GEN-01, GEN-02, GEN-03, GEN-04 | unit stubs | `uv run pytest tests/test_generator.py -x` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 0 | GEN-04 | config | `uv run pytest tests/test_generator.py -x` | ❌ W0 | ⬜ pending |
| 4-02-01 | 02 | 1 | GEN-02 | unit | `uv run pytest tests/test_generator.py::test_generate_email_success -x` | ❌ W0 | ⬜ pending |
| 4-02-02 | 02 | 1 | GEN-01 | unit | `uv run pytest tests/test_generator.py::test_prompt_includes_company_signals -x` | ❌ W0 | ⬜ pending |
| 4-03-01 | 03 | 1 | GEN-03 | unit | `uv run pytest tests/test_generator.py::test_retry_on_brackets -x` | ❌ W0 | ⬜ pending |
| 4-03-02 | 03 | 1 | GEN-03 | unit | `uv run pytest tests/test_generator.py::test_retry_on_word_count -x` | ❌ W0 | ⬜ pending |
| 4-03-03 | 03 | 1 | GEN-03 | unit | `uv run pytest tests/test_generator.py::test_retry_on_cliche -x` | ❌ W0 | ⬜ pending |
| 4-04-01 | 04 | 1 | GEN-04 | unit | `uv run pytest tests/test_generator.py::test_double_failure_returns_generation_failed -x` | ❌ W0 | ⬜ pending |
| 4-04-02 | 04 | 1 | GEN-04 | unit | `uv run pytest tests/test_generator.py::test_model_name_from_config -x` | ❌ W0 | ⬜ pending |
| 4-05-01 | 05 | 2 | GEN-02 | integration | `uv run pytest` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_generator.py` — stubs for GEN-01, GEN-02, GEN-03, GEN-04 (all 7 test functions)
- [ ] `profile.example.toml` — add `[generation]` section with `model = "llama-3.3-70b-versatile"`

*Existing pytest infrastructure (conftest.py, pyproject.toml config) covers all other requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Generated message reads naturally and is "send-ready" | GEN-02 | Subjective quality; no automated check | Run pipeline on 3 diverse URLs; read generated messages |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
