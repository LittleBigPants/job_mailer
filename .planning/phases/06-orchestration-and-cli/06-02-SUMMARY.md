---
phase: 06-orchestration-and-cli
plan: 02
subsystem: cli
tags: [typer, csv, idempotency, dry-run, deduplication]

# Dependency graph
requires:
  - phase: 06-orchestration-and-cli-01
    provides: Status.DRY_RUN enum value and 10 RED Phase 6 tests
  - phase: 05-sending-and-logging
    provides: send_email(), log_record(), outreach_log.csv pattern
provides:
  - Full pipeline with --dry-run flag (SEND-04)
  - Idempotency via outreach_log.csv pre-load (LOG-03)
  - Within-run URL deduplication via seen_urls set
  - --delay CLI flag overriding profile delay_seconds
  - Updated test_send_delay_called validating CLI priority chain
affects:
  - any future CLI phases

# Tech tracking
tech-stack:
  added: []
  patterns:
    - dry-run-branch: if dry_run block replaces send_email() entirely — not wrapping it
    - idempotency-preload: read outreach_log.csv once at startup into already_sent set
    - within-run-dedup: seen_urls set prevents double-processing within a single run
    - delay-resolution: delay if delay is not None else profile.get("send", {}).get("delay_seconds", 2)

key-files:
  created: []
  modified:
    - src/job_mailer/__main__.py
    - tests/test_cli.py

key-decisions:
  - "dry-run branch replaces send_email() entirely — set before the send call, not after"
  - "delay is not None check (not 'if delay') ensures 0 is a valid delay override"
  - "idempotency log read once before loop, not per-row — load_once pattern"
  - "test_send_delay_called updated to pass --delay 3 CLI flag; profile omits delay_seconds to validate priority chain"

patterns-established:
  - "Load idempotency state once before loop: read outreach_log.csv into set at startup"
  - "Within-run dedup: maintain seen_urls set; add url after first visit"

requirements-completed: [SEND-04, LOG-03]

# Metrics
duration: 1min
completed: 2026-03-15
---

# Phase 06 Plan 02: Dry-run, Idempotency, Dedup, and --delay Override Summary

**--dry-run flag, CSV idempotency pre-loader, within-run URL dedup, and --delay CLI override completing the full job-mailer pipeline with all 49 tests green**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-15T20:39:00Z
- **Completed:** 2026-03-15T20:40:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Rewrote `main()` with `--dry-run` and `--delay` Typer options; dry-run branch replaces `send_email()` entirely, logging with `status=dry_run`
- Idempotency: reads `outreach_log.csv` at startup into `already_sent` set; URLs with `status=sent` are silently skipped with no new log row
- Within-run deduplication via `seen_urls` set prevents double-processing duplicate CSV rows
- `--delay N` CLI flag takes priority over `profile.toml delay_seconds` over hardcoded default 2 via `delay if delay is not None else ...`
- Updated `test_send_delay_called` to invoke with `--delay 3`, profile without `delay_seconds`, confirming CLI priority chain
- All 49 tests pass GREEN (10 new Phase 6 tests + 39 pre-existing)

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite main() with dry-run, idempotency, --delay** - `e483173` (feat)
2. **Task 2: Update test_send_delay_called for --delay flag** - `41d698c` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `src/job_mailer/__main__.py` - Full pipeline rewrite with dry-run branch, idempotency loader, within-run dedup, --delay flag, updated summary lines
- `tests/test_cli.py` - test_send_delay_called updated to use --delay 3 CLI invocation

## Decisions Made
- `dry_run` branch placed before `send_email()` call — replaces it, does not wrap it; avoids accidental side effects
- `delay if delay is not None else ...` — 0 is a valid explicit delay, so truthiness check would be wrong
- Idempotency log read once before loop — no repeated I/O per row; matches RESEARCH.md guidance
- `monkeypatch.chdir(tmp_path)` added to `test_send_delay_called` — consistent with all idempotency tests

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — all 10 Phase 6 tests turned GREEN on first implementation attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 6 fully complete: all 49 tests pass, pipeline supports dry-run safety net and idempotency
- v1.0 milestone requirements SEND-04 and LOG-03 delivered
- No blockers for deployment

---
*Phase: 06-orchestration-and-cli*
*Completed: 2026-03-15*

## Self-Check: PASSED

- FOUND: src/job_mailer/__main__.py
- FOUND: tests/test_cli.py
- FOUND: .planning/phases/06-orchestration-and-cli/06-02-SUMMARY.md
- FOUND commit e483173: feat(06-02): rewrite main() with dry-run, idempotency, within-run dedup, --delay flag
- FOUND commit 41d698c: feat(06-02): update test_send_delay_called to use --delay 3 CLI flag
