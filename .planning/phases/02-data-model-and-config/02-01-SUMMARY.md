---
phase: 02-data-model-and-config
plan: 01
subsystem: testing
tags: [pytest, typer, tdd, test-scaffolds, wave-0]

# Dependency graph
requires:
  - phase: 01-scaffolding
    provides: "pyproject.toml, conftest.py, config.py, __main__.py — existing test infrastructure"
provides:
  - "Failing test stubs for CompanyRecord and Status enum (test_models.py)"
  - "Failing test stubs for CLI --input flag and exit behavior (test_cli.py)"
  - "Failing stubs for validate_profile() appended to test_config.py"
affects:
  - 02-02-models
  - 02-03-config
  - 02-04-cli

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave 0 test scaffolds: write failing stubs before any production code exists to enforce implementation order"
    - "Inline imports inside test functions for symbols-not-yet-existing: avoids blocking module collection while still enforcing RED state per test"

key-files:
  created:
    - tests/test_models.py
    - tests/test_cli.py
  modified:
    - tests/test_config.py

key-decisions:
  - "Import validate_profile inside each test function body (not at module top-level) so that module collection succeeds and existing Phase 1 tests stay GREEN while new stubs remain RED"
  - "test_cli_missing_input_flag asserts exit_code != 0 — current CLI with no required --input flag exits 0, so this correctly fails RED until --input is wired"

patterns-established:
  - "Wave 0 scaffold pattern: each stub imports the not-yet-existing symbol so plan execution order is enforced by test failures, not convention"

requirements-completed: [INPUT-01]

# Metrics
duration: 8min
completed: 2026-03-14
---

# Phase 2 Plan 01: Wave 0 Test Scaffolds Summary

**Three test files with failing stubs for CompanyRecord, Status enum, CLI --input flag, and validate_profile() — all RED until Wave 1 production code is written**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-14T21:23:10Z
- **Completed:** 2026-03-14T21:31:00Z
- **Tasks:** 1 (single TDD scaffold task)
- **Files modified:** 3

## Accomplishments

- Created `tests/test_models.py` with three stubs: `test_company_record_defaults`, `test_company_record_fields`, `test_status_enum_values` — all fail with ImportError (models.py absent)
- Created `tests/test_cli.py` with two stubs: `test_cli_input_exits_clean`, `test_cli_missing_input_flag` — both fail because `--input` flag not yet wired
- Appended two `validate_profile()` stubs to `tests/test_config.py` — fail with ImportError; all 5 existing Phase 1 tests still PASS without regression

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 test scaffolds** - `db90b2a` (test)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `tests/test_models.py` — Failing stubs for CompanyRecord instantiation and Status enum values
- `tests/test_cli.py` — Failing stubs for CLI --input argument and exit-clean behavior
- `tests/test_config.py` — Appended validate_profile() stubs (existing tests untouched)

## Decisions Made

- Import `validate_profile` inside each test function body rather than at module top-level. The module-level import caused a collection error that prevented the existing 5 Phase 1 tests from running at all. Moving the import inside the function body preserves RED state per-test while keeping the existing tests GREEN.
- `test_cli_missing_input_flag` correctly fails RED because the current CLI (no required args) exits 0. When `--input` becomes a required argument in Plan 02-04, this test will turn GREEN automatically.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Moved validate_profile import inside test function bodies**
- **Found during:** Task 1 (test_config.py append)
- **Issue:** Module-level `from job_mailer.config import validate_profile` caused an ImportError at collection time, blocking all 5 existing tests from running — violating the plan requirement that "the four existing Phase 1 tests must still PASS"
- **Fix:** Moved the import inside each test function body so module collection succeeds and per-test RED state is preserved
- **Files modified:** tests/test_config.py
- **Verification:** `uv run pytest tests/test_config.py -v` shows 5 PASSED + 1 FAILED (correct RED)
- **Committed in:** db90b2a (task commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in append approach)
**Impact on plan:** Fix required for correctness; new stubs still RED, no existing test regressions.

## Issues Encountered

None beyond the deviation documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All three test files in place; pytest collects and reports failures for all new stubs
- Plan 02-02 (models.py) will turn `tests/test_models.py` GREEN
- Plan 02-03 (config.py validate_profile) will turn the appended stubs GREEN
- Plan 02-04 (CLI --input wiring) will turn `tests/test_cli.py` GREEN

---
*Phase: 02-data-model-and-config*
*Completed: 2026-03-14*
