# Phase 6: Orchestration and CLI - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the full pipeline end-to-end with two remaining safety features: `--dry-run` (scrape and generate but never send) and idempotency (skip already-sent URLs on re-run). Also adds `--delay` as a proper CLI flag. The pipeline itself (scrape → generate → send → log → delay) is already implemented in Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Dry-run logging
- Log entries ARE written for dry-run rows — status value: `dry_run` (needs `DRY_RUN` added to `Status` enum)
- Terminal output per company: `[DRY RUN] {company_name} — {email_found} — {first N chars of generated_message}`
- Idempotency applies in dry-run mode — already-sent URLs are still skipped even during `--dry-run`
- Run summary uses a distinct prefix: `Done (dry run). X would send, Y failed, Z no email found.`

### Idempotency scope
- Only `status=sent` triggers a skip on re-run — failed, rate-limited, and dry-run entries are retried
- Deduplicate within the same run: if the same URL appears multiple times in the input CSV, only the first occurrence is processed; subsequent occurrences are silently skipped
- No terminal output for skipped rows — silent skip only
- Run summary includes a skipped count: `Done. X sent, Y skipped, Z failed, W no email found.`

### --delay CLI flag
- `--delay` on the CLI overrides `profile.toml`'s `delay_seconds` — CLI flag wins
- Default: 2 seconds when neither `--delay` nor `profile.toml` `delay_seconds` is set (matches REQUIREMENTS.md SEND-03 default)
- Integer only — no fractional seconds (Typer `int` type)
- Priority order: `--delay` CLI flag > `profile.toml` `delay_seconds` > hardcoded default of 2

### Claude's Discretion
- Message preview length for `[DRY RUN]` output (e.g. first 80 chars, truncated with `...`)
- How to load the existing log for idempotency check at startup (read into a set of sent URLs)
- Whether to add `DRY_RUN` to Status enum as `"dry_run"` string value

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `__main__.py`: full pipeline already wired — `scrape_company → generate_email → send_email → log_record → time.sleep(delay)`. Phase 6 adds `--dry-run` branch and idempotency check around this loop.
- `Status.SKIPPED`: already defined in enum — usable for within-run URL deduplication
- `CompanyRecord.to_csv_row()`: all 7 LOG-02 fields — idempotency loader reads the existing log with `csv.DictReader` filtering for `status == "sent"`
- `log_record()` in `logger.py`: already append-mode with header guard — dry-run entries go through the same path with `status=dry_run`

### Established Patterns
- `sys.exit(1)` for fatal errors (config invalid, daily quota exceeded)
- `typer.echo(err=True)` for per-row warnings
- Functions don't raise on expected failures — they return a populated `CompanyRecord` with the appropriate status

### Integration Points
- `__main__.py` `main()` function gets two new Typer options: `--dry-run` (bool flag) and `--delay` (int, optional)
- Idempotency: read existing log at startup into a `set[str]` of already-sent URLs before entering the CSV loop
- Within-run deduplication: maintain a `set[str]` of seen URLs across CSV rows during the loop

</code_context>

<specifics>
## Specific Ideas

- No specific product references — standard CLI tool conventions apply
- `[DRY RUN]` prefix is the distinguishing marker for dry-run terminal lines
- Summary line format exactly: `Done. X sent, Y skipped, Z failed, W no email found.` (real run) vs `Done (dry run). X would send, Y failed, Z no email found.` (dry run)

</specifics>

<deferred>
## Deferred Ideas

- `--log` flag for configurable log file path — not selected for discussion; Claude's Discretion on default (`outreach_log.csv` in CWD, as decided in Phase 5)
- `--limit N` flag (SAFE-01, v2) — future phase
- `--preview` flag (UX-01, v2) — future phase

</deferred>

---

*Phase: 06-orchestration-and-cli*
*Context gathered: 2026-03-15*
