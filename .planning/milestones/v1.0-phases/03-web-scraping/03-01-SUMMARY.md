---
phase: 03-web-scraping
plan: 01
subsystem: testing
tags: [pytest, pytest-httpx, tdd, httpx, enum]

# Dependency graph
requires:
  - phase: 02-data-model-and-config
    provides: Status enum and CompanyRecord dataclass used in test assertions
provides:
  - Nine failing test stubs in tests/test_scraper.py covering DISC-01 through DISC-04
  - Status.SCRAPE_FAILED enum value in models.py
  - pytest-httpx installed as dev dependency for HTTP mocking
affects:
  - 03-web-scraping (Plan 02 must make all nine tests pass)

# Tech tracking
tech-stack:
  added: [pytest-httpx==0.36.0]
  patterns: [TDD RED step — tests written before production code, httpx_mock fixture for HTTP response mocking]

key-files:
  created: [tests/test_scraper.py]
  modified: [src/job_mailer/models.py, tests/test_models.py, pyproject.toml, uv.lock]

key-decisions:
  - "pytest-httpx used for HTTP mocking — integrates with httpx natively via fixture injection"
  - "httpx_mock.add_exception used for ConnectError simulation rather than side_effect patterns"
  - "test_company_name_inference uses stripe.com as representative domain for capitalization inference"

patterns-established:
  - "RED-only TDD: tests in Wave 0 define the contract, production code follows in Wave 1"
  - "httpx_mock fixture: add_response(url=..., text=...) for 200 mocks, add_exception(..., url=...) for network errors"

requirements-completed: [DISC-01, DISC-02, DISC-03, DISC-04]

# Metrics
duration: 2min
completed: 2026-03-15
---

# Phase 3 Plan 01: Wave 0 Test Scaffolding Summary

**Nine failing scraper test stubs using pytest-httpx plus Status.SCRAPE_FAILED enum addition — RED contract for Plan 02 to satisfy**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-15T01:31:23Z
- **Completed:** 2026-03-15T01:33:10Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added `Status.SCRAPE_FAILED = "scrape_failed"` to the Status enum and updated test_models.py (now 7 members, all GREEN)
- Installed pytest-httpx dev dependency for httpx response/exception mocking
- Created tests/test_scraper.py with nine named test functions covering all four DISC requirements plus email priority, exclusion, and company name inference
- All nine tests fail RED with `ModuleNotFoundError: No module named 'job_mailer.scraper'` — contract established

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Status.SCRAPE_FAILED and install pytest-httpx** - `4f727b4` (feat)
2. **Task 2: Write failing test stubs in test_scraper.py** - `ea0f222` (test)

_Note: This plan is purely Wave 0 RED — no GREEN or REFACTOR commits; those occur in Plan 02._

## Files Created/Modified
- `tests/test_scraper.py` - Nine failing test stubs for scrape_company() covering DISC-01 through DISC-04
- `src/job_mailer/models.py` - Added SCRAPE_FAILED = "scrape_failed" to Status enum
- `tests/test_models.py` - Updated expected_values set to include "scrape_failed" (6 → 7 members)
- `pyproject.toml` - pytest-httpx added as dev dependency
- `uv.lock` - Updated lockfile

## Decisions Made
- pytest-httpx chosen for HTTP mocking — it provides a purpose-built `httpx_mock` pytest fixture that integrates cleanly with httpx's async/sync client, avoiding complex monkeypatching
- `httpx_mock.add_exception(httpx.ConnectError("timeout"), url=...)` per-URL for `test_scrape_failed` to simulate three consecutive network failures
- Stripe used in `test_company_name_inference` as a well-known single-word domain that tests capitalization inference cleanly

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 02 can import the nine tests immediately and begin making them pass
- `from job_mailer.scraper import scrape_company` is the import contract — Plan 02 must create src/job_mailer/scraper.py with that function
- `Status.SCRAPE_FAILED` is available for Plan 02 to use when network errors occur
- All pre-existing tests (12) remain GREEN

---
*Phase: 03-web-scraping*
*Completed: 2026-03-15*
