# Phase 5: Sending and Logging - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Send emails via the Resend API and immediately write a complete log record for every company attempt — whether the send succeeded, hit a rate limit, hit the daily quota, or failed with an invalid address. Configurable send delay between emails. Dry-run flag, idempotency (skip-already-sent), and full CLI orchestration are Phase 6.

</domain>

<decisions>
## Implementation Decisions

### Error status mapping
- Resend 429 rate-limit → log status: `rate_limited` (add `RATE_LIMITED` to Status enum)
- Resend `daily_quota_exceeded` → log status: `rate_limited` (same status — daily quota is a rate limit variant; keeps enum minimal)
- Resend `invalid_email` → log status: `send_failed` (permanent failure, not retryable — reuses existing enum value)
- All other Resend errors → log status: `send_failed`
- Only three error types modeled explicitly: 429, daily_quota_exceeded, invalid_email

### daily_quota_exceeded behavior
- Abort the entire run immediately — no point continuing when the daily quota is exhausted
- Log the triggering company as `rate_limited` before exiting
- Terminal message format: `"ERROR: Resend daily quota exceeded. Sent N emails this run. Remaining companies not processed."`
- Companies not yet attempted: do NOT appear in the log (they stay in the input CSV; re-run picks them up naturally)

### Terminal output during sends
- Per-company success line: `"  {company_name} — {email} — sent"` — matches existing scrape/generate echo pattern
- Rate-limited line: `"  WARNING: {company_name} — rate_limited (429)"` — consistent with Phase 3/4 WARNING pattern; run continues after logging
- Send delay: silent — no countdown or "Waiting..." output; per-company lines appear at the delay interval
- Run summary on completion: `"Done. X sent, Y failed, Z no email found."` — covers all terminal statuses in a single line

### Log file
- Claude's Discretion on default filename and location (suggested: `outreach_log.csv` in the working directory)
- Log file path configurable in Phase 6 via CLI flag

### Claude's Discretion
- Resend Python client choice (resend library vs. httpx direct)
- Exact field name used to inspect Resend error type (inspect the response object, not HTTP status)
- `sender.py` module name and function signature
- `logger.py` module name and function signature (or inline in `__main__.py`)
- CSV writer fieldnames order (must match LOG-02 fields: url, company_name, email_found, generated_message, status, resend_message_id, timestamp)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CompanyRecord.to_csv_row()` (models.py): returns all 7 LOG-02 fields as a flat dict — use directly with `csv.DictWriter`
- `Status` enum (models.py): `SEND_FAILED` already defined; `RATE_LIMITED` needs to be added
- `__main__.py`: current pipeline calls `scrape_company()` then `generate_email()` per row — Phase 5 adds `send_email()` and `log_record()` calls after generate succeeds

### Established Patterns
- Synchronous pipeline throughout — no async; Resend API call is a blocking HTTP call
- `sys.exit()` for fatal errors (daily_quota_exceeded abort fits here); `typer.echo(err=True)` for per-row failures
- Functions return populated `CompanyRecord` without raising on expected failures — `send_email()` should match this interface
- Echo pattern: `"  {company} — {field} — {status}"` for per-row output (all prior phases)

### Integration Points
- `__main__.py` currently echoes scrape/generate status; Phase 5 replaces that echo with a send call + log write + new echo
- CSV log must be opened in append mode (`newline=""`, `mode="a"`) to support immediate per-row writes
- Send delay: `time.sleep(delay_seconds)` between loop iterations; delay value from `profile.toml` or `--delay` flag (Phase 6 adds CLI flag; Phase 5 reads from profile only)

</code_context>

<specifics>
## Specific Ideas

- `rate_limited` reused for both 429 and `daily_quota_exceeded` — keeps enum minimal without losing meaningful distinction from `send_failed`
- Run summary format: `"Done. X sent, Y failed, Z no email found."` — covers the key outcome categories in one line
- Companies not processed when quota hits: stay in input CSV, not in log — re-run idempotency (Phase 6) handles picking them back up

</specifics>

<deferred>
## Deferred Ideas

- Log file path as a CLI `--log` flag — Phase 6 (orchestration adds remaining CLI flags)
- `--limit N` flag (SAFE-01, v2) — future phase
- `--preview` flag (UX-01, v2) — future phase

</deferred>

---

*Phase: 05-sending-and-logging*
*Context gathered: 2026-03-15*
