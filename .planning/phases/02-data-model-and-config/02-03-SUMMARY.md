---
phase: 02-data-model-and-config
plan: 03
subsystem: config
tags: [python, tomllib, validation, sys.exit, profile]

# Dependency graph
requires:
  - phase: 02-01
    provides: Wave 0 validate_profile test stubs in test_config.py
  - phase: 01-03
    provides: load_profile() and check_env() in config.py
provides:
  - validate_profile(profile: dict) -> None — raises SystemExit listing all missing field dot-paths
  - _REQUIRED_PROFILE_FIELDS module-level constant with 5 required field tuples
  - Complete config.py with check_env, load_profile, validate_profile exports
affects:
  - 02-04 (CLI wiring: validate_profile called after load_profile)
  - All phases that consume developer profile fields

# Tech tracking
tech-stack:
  added: []
  patterns: [collect-all-then-exit validation pattern (report all missing fields at once), dot-path traversal for nested dict validation]

key-files:
  created: []
  modified: [src/job_mailer/config.py]

key-decisions:
  - "validate_profile() collects all missing fields before calling sys.exit() once — gives user a complete error list rather than one-at-a-time"
  - "_REQUIRED_PROFILE_FIELDS as module-level constant makes required schema easy to audit and extend"

patterns-established:
  - "Collect-all-then-exit: gather all validation errors before calling sys.exit() so user sees complete picture"
  - "Dot-path reporting: missing fields reported as 'developer.contact.email' not raw dict key names"

requirements-completed: [INPUT-01]

# Metrics
duration: 1min
completed: 2026-03-14
---

# Phase 2 Plan 03: validate_profile() for Config Validation Summary

**validate_profile() added to config.py using collect-all-then-exit pattern, reporting all missing profile.toml dot-paths in one sys.exit() call**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-14T21:26:43Z
- **Completed:** 2026-03-14T21:27:30Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Appended `_REQUIRED_PROFILE_FIELDS` module-level constant with 5 required field tuples matching profile.example.toml schema
- Implemented `validate_profile()` that traverses nested dict using tuple key paths and collects all missing fields before exiting
- All 7 test_config.py tests pass: 5 Phase 1 originals + 2 Phase 2 validate_profile stubs (previously RED)
- Existing check_env() and load_profile() functions left completely untouched

## Task Commits

Each task was committed atomically:

1. **Task 1: Add validate_profile() to config.py** - `07353fe` (feat)

**Plan metadata:** (docs commit pending)

_Note: TDD task — RED state confirmed before implementation (ImportError on validate_profile import), GREEN after_

## Files Created/Modified

- `src/job_mailer/config.py` - Appended _REQUIRED_PROFILE_FIELDS constant and validate_profile() function after load_profile()

## Decisions Made

- validate_profile() collects all missing fields before calling sys.exit() once — follows the established pattern from check_env() and gives users a complete error list rather than stopping at the first missing field
- _REQUIRED_PROFILE_FIELDS as module-level constant (not inline) keeps the required schema auditable and separable from the traversal logic

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- test_cli.py pre-existing RED stub (test_cli_input_exits_clean) was confirmed as a planned failure from Phase 2 Wave 0 scaffolding. It remains RED until Plan 02-04 wires up the CLI --input flag. Not caused by this plan's changes. Out of scope per deviation boundary rules.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- config.py now exports all three symbols: check_env, load_profile, validate_profile
- Plan 02-04 (CLI wiring) can import validate_profile immediately after load_profile()
- All test_config.py tests green — no regressions to resolve before proceeding

---
*Phase: 02-data-model-and-config*
*Completed: 2026-03-14*
