---
phase: 03-web-scraping
plan: "03"
subsystem: cli
tags: [csv, typer, scraper, integration, tdd]

# Dependency graph
requires:
  - phase: 03-02
    provides: scrape_company() function in scraper.py returning CompanyRecord
  - phase: 02-data-model-and-config
    provides: CompanyRecord dataclass, Status enum, check_env/load_profile/validate_profile
provides:
  - End-to-end CLI that reads a CSV of URLs and runs scrape_company() per row
  - Per-row summary output with company name, email, and status
  - Error-resilient loop that catches per-row failures and continues
  - Integration test confirming scraper is called from CLI
affects: [04-llm-generation, 05-email-delivery]

# Tech tracking
tech-stack:
  added: [csv stdlib]
  patterns: [CSV reading via csv.reader with header skip, per-row exception handling with warning output, typer echo for CLI output]

key-files:
  created: []
  modified: [src/job_mailer/__main__.py, tests/test_cli.py]

key-decisions:
  - "scrape_company imported at module level in __main__.py — enables clean patching via job_mailer.__main__.scrape_company in tests"
  - "Per-row exception catch with typer.echo(..., err=True) — failure on one URL does not abort the full batch"
  - "Header row skipped by exact string match url (case-insensitive) — simple and sufficient for single-column CSV format"

patterns-established:
  - "TDD RED committed before implementation — failing test verifies patch target exists before production code is written"
  - "test_cli_input_exits_clean (no mock) passes because scrape exceptions are swallowed — validates resilience under real failure conditions"

requirements-completed: [DISC-01, DISC-02, DISC-03, DISC-04]

# Metrics
duration: 8min
completed: 2026-03-15
---

# Phase 3 Plan 03: CLI Scraper Integration Summary

**CSV-to-scraper pipeline wired into CLI — reads single-column URL CSV, calls scrape_company() per row, prints name/email/status summary, catches per-row failures without aborting**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-15T01:32:00Z
- **Completed:** 2026-03-15T01:40:19Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Replaced stub `typer.echo` in `__main__.py` with a full CSV reading loop using `csv.reader`
- Integrated `scrape_company()` call per URL row with per-row exception handling
- Added `test_cli_runs_scraper_per_url` integration test that patches `scrape_company` and asserts output fields
- Full 22-test suite remains GREEN after changes

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing scraper integration test** - `557b1f5` (test)
2. **Task 1 GREEN: Wire scraper into CLI with CSV reading loop** - `34ce3b1` (feat)

_Note: Task 2 test was written as part of Task 1 TDD RED phase and satisfied all Task 2 requirements without additional changes._

## Files Created/Modified

- `src/job_mailer/__main__.py` - Added `import csv` and `from job_mailer.scraper import scrape_company`; replaced stub echo with CSV loop, scrape call, summary output, per-row error handling
- `tests/test_cli.py` - Added `test_cli_runs_scraper_per_url` with `tmp_path`, `patch`, `CompanyRecord` mock return, exit code and output assertions

## Decisions Made

- `scrape_company` imported at module level in `__main__.py` — enables clean `unittest.mock.patch("job_mailer.__main__.scrape_company")` patching in tests without needing `create=True`
- Per-row exception catch writes to `err=True` stream — warnings go to stderr, main output to stdout, keeping them separable
- Header skip uses exact `url.lower() == "url"` check — deliberately simple, sufficient for the single-column format established in prior plans

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — existing `test_cli_input_exits_clean` test (no mock) continued to pass after integration because scrape failures are caught in the loop and the CLI still exits 0.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 3 is complete: given a CSV of URLs, the tool discovers emails or reports clear failure status
- `__main__.py` is ready for Phase 4 (LLM generation) to add a `generate_email(record, profile)` call after `scrape_company()`
- The existing CSV loop structure accommodates additional pipeline steps between scrape and output

---
*Phase: 03-web-scraping*
*Completed: 2026-03-15*
