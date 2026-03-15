---
phase: 01-scaffolding
plan: 02
subsystem: infra
tags: [python, config, dotenv, tomllib, pytest, tdd, environment-validation]

# Dependency graph
requires:
  - phase: 01-scaffolding plan 01
    provides: src/job_mailer package importable, .venv with dev dependencies, pyproject.toml pytest config
provides:
  - src/job_mailer/config.py with load_dotenv() at module top, check_env(), load_profile()
  - tests/test_config.py with 5 passing unit tests covering INFRA-02 and INFRA-03
  - tests/conftest.py with autouse fixture preventing env var test pollution
  - tests/__init__.py making tests a package
affects:
  - All phases that import from job_mailer (check_env must be called at startup)
  - Phase 4 (LLM generation — load_profile() supplies developer context to prompt)
  - Phase 5 (sending — load_profile() supplies contact info and from address logic)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - load_dotenv() at module top-level (not inside a function) — prevents intermittent missing-key bugs in tests
    - sys.exit() with named missing keys (not raise ValueError or KeyError traceback)
    - tomllib.load() in binary mode "rb" — stdlib requirement
    - autouse conftest fixture clears env keys before each test to prevent pollution

key-files:
  created:
    - src/job_mailer/config.py
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_config.py
  modified: []

key-decisions:
  - "load_dotenv() placed at module top-level per RESEARCH.md pitfall — calling inside a function would miss keys already read by other modules"
  - "sys.exit() used instead of raising exceptions — caller gets an actionable human message, not a traceback"
  - "autouse conftest fixture clears all three env keys before each test — prevents load_dotenv() side effects from leaking between tests"

patterns-established:
  - "Pattern: config.py as startup contract — all other modules import check_env from here; validation runs before any API call"
  - "Pattern: conftest.py autouse fixture for env var isolation — required when module-level load_dotenv() exists"

requirements-completed: [INFRA-02, INFRA-03]

# Metrics
duration: 1min
completed: 2026-03-14
---

# Phase 1 Plan 02: Startup Config Validation Summary

**TDD-implemented config module: check_env() validates 3 env keys via sys.exit with named missing keys; load_profile() reads profile.toml via tomllib; 5 tests pass in RED-GREEN cycle**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-14T19:52:16Z
- **Completed:** 2026-03-14T19:53:05Z
- **Tasks:** 2 (RED + GREEN)
- **Files modified:** 4

## Accomplishments
- Wrote 5 failing tests covering all required check_env() and load_profile() behaviors (RED)
- Implemented config.py with load_dotenv() at module top, check_env(), and load_profile() (GREEN)
- All 5 tests pass: pytest tests/test_config.py -x exits 0
- conftest.py autouse fixture ensures env var isolation across all tests

## Task Commits

Each task was committed atomically:

1. **RED: Add failing tests for check_env and load_profile** - `91ee84b` (test)
2. **GREEN: Implement check_env and load_profile** - `0fb9b1e` (feat)

**Plan metadata:** *(docs commit — see below)*

_TDD plan: RED commit (failing tests), GREEN commit (implementation making all tests pass)_

## Files Created/Modified
- `src/job_mailer/config.py` - load_dotenv() at module top; check_env() validates GROQ_API_KEY, RESEND_API_KEY, RESEND_FROM_EMAIL; load_profile() reads TOML via tomllib
- `tests/__init__.py` - makes tests a Python package
- `tests/conftest.py` - autouse fixture that clears the 3 required env keys before each test
- `tests/test_config.py` - 5 unit tests: 3 for check_env() and 2 for load_profile()

## Decisions Made
- **load_dotenv() at module top-level:** Per RESEARCH.md Pitfall 3 — calling inside a function means it might run after another module has already read os.environ; module-level placement guarantees it runs on import.
- **autouse conftest fixture:** load_dotenv() runs at import time and could pollute the environment between tests; autouse fixture ensures each test starts with a clean slate.
- **sys.exit() not raise:** Produces a human-readable message instead of a raw exception traceback; required by INFRA-02 and explicitly tested in test_check_env_names_missing_key.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None — all tests moved cleanly from RED to GREEN in one implementation pass.

## User Setup Required
None - no external service configuration required at this stage.

## Next Phase Readiness
- `from job_mailer.config import check_env, load_profile` works in the venv
- 5 tests provide regression coverage for config behavior
- check_env() and load_profile() ready to be called from __main__.py at startup
- No blockers for Plan 03

## Self-Check: PASSED

- FOUND: src/job_mailer/config.py
- FOUND: tests/__init__.py
- FOUND: tests/conftest.py
- FOUND: tests/test_config.py
- FOUND commit: 91ee84b (test(01-02): add failing tests for check_env and load_profile)
- FOUND commit: 0fb9b1e (feat(01-02): implement check_env and load_profile)

---
*Phase: 01-scaffolding*
*Completed: 2026-03-14*
