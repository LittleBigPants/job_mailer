---
phase: 04-llm-generation
plan: "01"
subsystem: testing
tags: [tdd, groq, llm, generator, pytest]

# Dependency graph
requires:
  - phase: 03-web-scraping
    provides: CompanyRecord dataclass and scrape_company interface pattern
  - phase: 02-data-model-and-config
    provides: Status enum, CompanyRecord, load_profile dict structure
provides:
  - Seven failing test stubs covering GEN-01 through GEN-04 in tests/test_generator.py
  - [generation] section with model key documented in profile.example.toml
affects:
  - 04-02 (must implement generator.py to turn these stubs green)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED-first: test file imports non-existent module to enforce RED state before implementation"
    - "MagicMock with side_effect=[r1, r2] for multi-call retry simulation"
    - "Minimal profile dict fixture (_make_profile) with optional model override for model-config test"

key-files:
  created:
    - tests/test_generator.py
  modified:
    - profile.example.toml

key-decisions:
  - "Profile fixture omits [generation] key by default — exercises the fallback path; only test_model_name_from_config passes a model key"
  - "call_args accessed via both positional and keyword paths to handle either Groq call signature"
  - "test_double_failure_returns_generation_failed uses two bracket-placeholder responses — simplest way to guarantee both fail the same validation rule"

patterns-established:
  - "Model-name assertion: extract model from call_args[1].get('model') or call_args[0][1] to tolerate positional or keyword Groq invocation"

requirements-completed: [GEN-01, GEN-02, GEN-03, GEN-04]

# Metrics
duration: 2min
completed: 2026-03-15
---

# Phase 4 Plan 01: LLM Generation TDD Red State Summary

**Seven failing test stubs plus profile.example.toml [generation] section establishing TDD RED state before generator.py is written**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-15T08:40:57Z
- **Completed:** 2026-03-15T08:42:01Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created tests/test_generator.py with 7 test stubs — all in RED state (ModuleNotFoundError for job_mailer.generator)
- Added [generation] section with model key and comment to profile.example.toml
- Verified 22 Phase 1-3 tests remain green after additions

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing test stubs for generator.py** - `05224e9` (test)
2. **Task 2: Add [generation] section to profile.example.toml** - `03c0119` (chore)

## Files Created/Modified

- `tests/test_generator.py` - Seven failing test stubs covering GEN-01 through GEN-04; RED state enforced via top-level import of non-existent generator module
- `profile.example.toml` - Appended [generation] section documenting model key with default llama-3.3-70b-versatile

## Decisions Made

- Profile dict fixture omits [generation] key by default to exercise the fallback path; only test_model_name_from_config adds the key — this validates that the implementation uses a sensible default when the key is absent
- call_args accessed via both positional and keyword lookup to tolerate either Groq call signature in Plan 02's implementation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RED state confirmed: `uv run pytest tests/test_generator.py` exits non-zero with ModuleNotFoundError
- All existing tests green: 22/22 pass
- Plan 02 (04-02) must create src/job_mailer/generator.py to turn all seven stubs green
- Blocker noted in STATE.md: Groq model name `llama-3.3-70b-versatile` should be confirmed against Groq console at Plan 02 implementation time

---
*Phase: 04-llm-generation*
*Completed: 2026-03-15*
