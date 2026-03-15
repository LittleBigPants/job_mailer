---
phase: 04-llm-generation
plan: "02"
subsystem: api
tags: [groq, llm, generator, tdd, retry, validation]

# Dependency graph
requires:
  - phase: 04-llm-generation
    provides: Seven failing test stubs in test_generator.py (TDD RED state)
  - phase: 02-data-model-and-config
    provides: CompanyRecord dataclass, Status enum, load_profile dict structure
provides:
  - generate_email(record, profile) public function in src/job_mailer/generator.py
  - CLICHE_DENY_LIST module-level constant
  - Private validation helpers (_word_count, _has_brackets, _has_cliche, _validate, _build_messages)
affects:
  - 04-03 (any CLI wiring that calls generate_email)
  - 05-email-sending (needs generate_email to populate generated_message before send)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Groq client instantiated inside generate_email() — not at module level — avoids key timing issues in tests"
    - "Multi-turn retry: append assistant+user turns with failure reason string to messages list before second call"
    - "Validate then retry: word count check first, then brackets, then cliche — deterministic order"
    - "No-exception interface: all Groq API errors caught, echoed to stderr with typer, return GENERATION_FAILED"

key-files:
  created:
    - src/job_mailer/generator.py
  modified: []

key-decisions:
  - "Groq client instantiated inside generate_email() body — matches plan spec; prevents ImportError side-effects during test collection"
  - "All keyword arguments passed to chat.completions.create() (messages=, model=) — required by test call_args inspection patterns"
  - "_validate() check order: word count first, then brackets, then cliche — consistent with plan spec"

patterns-established:
  - "Retry failure reason messages are exact strings as specified in plan — tests assert substrings ('bracket', 'cliche', 'opener', 'N words')"

requirements-completed: [GEN-01, GEN-02, GEN-03, GEN-04]

# Metrics
duration: 2min
completed: 2026-03-15
---

# Phase 4 Plan 02: LLM Generation Implementation Summary

**Groq-backed generate_email() with word-count/bracket/cliche validation and single-retry using embedded failure reason in multi-turn message history**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-15T08:43:49Z
- **Completed:** 2026-03-15T08:46:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created src/job_mailer/generator.py implementing generate_email() and all private helpers
- All 7 tests in test_generator.py turned GREEN (TDD GREEN state achieved)
- Full test suite 29/29 passes — no regressions in Phase 1-3 tests
- Groq client correctly scoped inside function body to avoid module-level import side-effects

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement generate_email() with validation and retry logic** - `73a80c7` (feat)

## Files Created/Modified

- `src/job_mailer/generator.py` - Public `generate_email(record, profile) -> CompanyRecord` plus CLICHE_DENY_LIST constant and private helpers (_word_count, _has_brackets, _has_cliche, _validate, _build_messages)

## Decisions Made

- Passed `messages` and `model` as keyword arguments to `chat.completions.create()` — the test file inspects `call_args[1].get("messages")` and `call_args[1].get("model")`, so keyword-only invocation is required for test compatibility
- Groq client instantiated inside `generate_email()` body, not at module level — avoids import-time side-effects and matches the established pattern from scraper.py
- `_validate()` checks word count first, then brackets, then cliche — deterministic order matches plan specification

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. GROQ_API_KEY is already documented in .env.example from Phase 1 scaffolding.

## Next Phase Readiness

- generate_email() is production-ready with full validation and retry logic
- All GEN-01 through GEN-04 requirements satisfied by passing tests
- Full suite 29/29 green — safe to continue
- Phase 4 Plan 03 (if any) or Phase 5 (email sending) can import generate_email from job_mailer.generator

---
*Phase: 04-llm-generation*
*Completed: 2026-03-15*
