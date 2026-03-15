---
phase: 3
slug: web-scraping
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already configured in pyproject.toml) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_scraper.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_scraper.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 0 | DISC-04 (support) | unit | `uv run pytest tests/test_models.py -x` | Update existing | ⬜ pending |
| 3-01-02 | 01 | 0 | DISC-01 | unit | `uv run pytest tests/test_scraper.py -x` | ❌ W0 | ⬜ pending |
| 3-02-01 | 02 | 1 | DISC-01 | unit | `uv run pytest tests/test_scraper.py::test_homepage_mailto_email -x` | ✅ W0 | ⬜ pending |
| 3-02-02 | 02 | 1 | DISC-01 | unit | `uv run pytest tests/test_scraper.py::test_homepage_text_email -x` | ✅ W0 | ⬜ pending |
| 3-02-03 | 02 | 1 | DISC-02 | unit | `uv run pytest tests/test_scraper.py::test_contact_fallback -x` | ✅ W0 | ⬜ pending |
| 3-02-04 | 02 | 1 | DISC-03 | unit | `uv run pytest tests/test_scraper.py::test_about_fallback -x` | ✅ W0 | ⬜ pending |
| 3-02-05 | 02 | 1 | DISC-04 | unit | `uv run pytest tests/test_scraper.py::test_no_email_found -x` | ✅ W0 | ⬜ pending |
| 3-02-06 | 02 | 1 | DISC-04 | unit | `uv run pytest tests/test_scraper.py::test_scrape_failed -x` | ✅ W0 | ⬜ pending |
| 3-02-07 | 02 | 1 | (support) | unit | `uv run pytest tests/test_scraper.py::test_email_priority -x` | ✅ W0 | ⬜ pending |
| 3-02-08 | 02 | 1 | (support) | unit | `uv run pytest tests/test_scraper.py::test_never_return_excluded -x` | ✅ W0 | ⬜ pending |
| 3-02-09 | 02 | 1 | (support) | unit | `uv run pytest tests/test_scraper.py::test_company_name_inference -x` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_scraper.py` — stubs covering DISC-01 through DISC-04 and supporting priority/inference tests; requires `pytest-httpx` for httpx mocking
- [ ] `src/job_mailer/models.py` update — add `SCRAPE_FAILED = "scrape_failed"` to `Status` enum
- [ ] `tests/test_models.py` update — add `"scrape_failed"` to `expected_values` set in `test_status_enum_values`
- [ ] `uv add --dev pytest-httpx` — install test dependency (v0.36.0)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| JS-obfuscated emails not resolved | DISC-01 | Headless browser out of scope; cannot automate without Playwright | Verify in KNOWN_LIMITATION.md or acceptance notes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
