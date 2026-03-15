# Phase 5: Sending and Logging - Research

**Researched:** 2026-03-15
**Domain:** Resend Python SDK email sending, CSV append-mode logging, error handling
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Error status mapping:**
- Resend 429 rate-limit -> log status: `rate_limited` (add `RATE_LIMITED` to Status enum)
- Resend `daily_quota_exceeded` -> log status: `rate_limited` (same status — daily quota is a rate limit variant)
- Resend `invalid_email` -> log status: `send_failed` (permanent failure, not retryable — reuses existing enum value)
- All other Resend errors -> log status: `send_failed`
- Only three error types modeled explicitly: 429, daily_quota_exceeded, invalid_email

**daily_quota_exceeded behavior:**
- Abort the entire run immediately — no point continuing when the daily quota is exhausted
- Log the triggering company as `rate_limited` before exiting
- Terminal message format: `"ERROR: Resend daily quota exceeded. Sent N emails this run. Remaining companies not processed."`
- Companies not yet attempted: do NOT appear in the log (they stay in the input CSV; re-run picks them up naturally)

**Terminal output during sends:**
- Per-company success line: `"  {company_name} — {email} — sent"` — matches existing scrape/generate echo pattern
- Rate-limited line: `"  WARNING: {company_name} — rate_limited (429)"` — consistent with Phase 3/4 WARNING pattern; run continues after logging
- Send delay: silent — no countdown or "Waiting..." output; per-company lines appear at the delay interval
- Run summary on completion: `"Done. X sent, Y failed, Z no email found."` — covers all terminal statuses in a single line

**Log file:**
- Claude's Discretion on default filename and location (suggested: `outreach_log.csv` in the working directory)
- Log file path configurable in Phase 6 via CLI flag

### Claude's Discretion
- Resend Python client choice (resend library vs. httpx direct)
- Exact field name used to inspect Resend error type (inspect the response object, not HTTP status)
- `sender.py` module name and function signature
- `logger.py` module name and function signature (or inline in `__main__.py`)
- CSV writer fieldnames order (must match LOG-02 fields: url, company_name, email_found, generated_message, status, resend_message_id, timestamp)

### Deferred Ideas (OUT OF SCOPE)
- Log file path as a CLI `--log` flag — Phase 6 (orchestration adds remaining CLI flags)
- `--limit N` flag (SAFE-01, v2) — future phase
- `--preview` flag (UX-01, v2) — future phase
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SEND-01 | Sends email via Resend API using credentials from .env | `resend` library is already in pyproject.toml (v2.23.0+); `resend.api_key = os.environ["RESEND_API_KEY"]` then `resend.Emails.send(params)` |
| SEND-02 | Inspects Resend response object for named error types (429 rate limit, daily_quota_exceeded, invalid_email) — not just HTTP status code | Catch `resend.exceptions.RateLimitError` and `resend.exceptions.ValidationError`; inspect `.error_type` attribute for `"daily_quota_exceeded"` vs `"rate_limit_exceeded"`; inspect `.error_type` for `"invalid_from_address"` or validation variants |
| SEND-03 | Configurable delay between sends (default: 2s; configurable via profile.toml or --delay CLI flag) | `profile["send"]["delay_seconds"]` already in profile.example.toml; `time.sleep(delay)` between loop iterations; `--delay` CLI flag is Phase 6 |
| LOG-01 | Append-only CSV log is written immediately after each company attempt (before moving to next row) | `csv.DictWriter` with `mode="a"`, `newline=""`, write header only if file doesn't exist; flush after every row |
| LOG-02 | Log captures: url, company_name, email_found, generated_message, status, resend_message_id, timestamp | `CompanyRecord.to_csv_row()` already returns all 7 fields as a flat dict — use directly with `csv.DictWriter` |
</phase_requirements>

---

## Summary

Phase 5 adds two new concerns to the existing synchronous pipeline: (1) calling the Resend API to send emails, and (2) writing a complete log record to a CSV file immediately after each attempt. Both concerns are simple to implement because the project's prior phases already set up all the foundations — `CompanyRecord.to_csv_row()` returns all 7 log fields, `Status.SEND_FAILED` already exists, and the pipeline in `__main__.py` has a clear slot to insert the send+log step after `generate_email()`.

The most technically precise part of this phase is error discrimination: the Resend SDK raises a single `RateLimitError` class for all 429 responses — `rate_limit_exceeded`, `daily_quota_exceeded`, and `monthly_quota_exceeded`. To distinguish these subtypes, inspect `exc.error_type`, which carries the API's `"name"` field verbatim. For non-429 errors (including `invalid_from_address`), the SDK raises `ValidationError` or `ResendError` with appropriate `error_type` values. The base catch-all is `resend.exceptions.ResendError`.

CSV append-mode logging is a two-step concern: header management (write header only when file does not yet exist) and immediate flushing (write one row per company attempt before advancing the loop). Python's stdlib `csv.DictWriter` handles both without extra libraries. The `outreach_log.csv` default in the working directory is consistent with the project's "works from repo root" UX principle.

**Primary recommendation:** Use the `resend` library (already declared in pyproject.toml at v2.23.0+); catch `resend.exceptions.RateLimitError` and inspect `.error_type` for subtype discrimination; use stdlib `csv.DictWriter` in append mode with immediate row-level writes.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `resend` | >=2.23.0 (already in pyproject.toml) | Send email via Resend API | Already declared; SDK 2.0 redesign is stable; exception hierarchy is well-structured |
| `csv` (stdlib) | Python 3.11+ built-in | Append-mode CSV log writing | No external dependency; `DictWriter` maps directly to `CompanyRecord.to_csv_row()` output |
| `time` (stdlib) | Python 3.11+ built-in | `time.sleep()` for send delay | No alternative needed; synchronous pipeline established in all prior phases |
| `os` (stdlib) | Python 3.11+ built-in | `os.environ["RESEND_API_KEY"]` | Already used in config.py; consistent pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `resend.exceptions` | part of resend package | Typed exception classes for error discrimination | Always import from here, not from `resend` directly |
| `pathlib.Path` | stdlib | Check if log file exists (header decision) | `Path(log_path).exists()` to decide whether to write CSV header |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `resend` library | `httpx` direct API calls | httpx avoids SDK dependency but requires hand-rolling JSON parsing, error mapping, and status-code inspection — the SDK already does this correctly |

**Installation:** No new packages needed — `resend>=2.23.0` is already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure

Phase 5 adds two new source files:

```
src/job_mailer/
├── __main__.py      # extended: add send_email + log_record calls; send delay loop; run summary
├── sender.py        # NEW: send_email(record, profile) -> CompanyRecord
├── logger.py        # NEW: log_record(record, log_path) -> None
├── models.py        # extended: add Status.RATE_LIMITED
├── config.py        # unchanged
├── generator.py     # unchanged
└── scraper.py       # unchanged
```

### Pattern 1: send_email() Function Signature

**What:** A function that takes a populated `CompanyRecord` (with `email_found` and `generated_message` set), calls the Resend API, and returns the record with `status` and `resend_message_id` updated. Never raises on expected Resend errors — returns the record with the appropriate status instead.

**When to use:** After `generate_email()` succeeds and `record.generated_message` is set.

**Example:**
```python
# Source: resend.exceptions (inspected from installed package 2026-03-15)
import os
import resend
import resend.exceptions

from job_mailer.models import CompanyRecord, Status


def send_email(record: CompanyRecord, profile: dict) -> CompanyRecord:
    """Send email via Resend. Returns record with status and resend_message_id set.

    Never raises on expected Resend errors — returns record with
    Status.SEND_FAILED or Status.RATE_LIMITED instead.

    Raises:
        SystemExit: Only on daily_quota_exceeded (caller must handle).
    """
    resend.api_key = os.environ["RESEND_API_KEY"]
    from_email = os.environ["RESEND_FROM_EMAIL"]

    params: resend.Emails.SendParams = {
        "from": from_email,
        "to": [record.email_found],
        "subject": f"Reaching out — {record.company_name}",
        "text": record.generated_message,
    }

    try:
        response = resend.Emails.send(params)
        record.resend_message_id = response.id
        record.status = Status.SENT
    except resend.exceptions.RateLimitError as exc:
        record.status = Status.RATE_LIMITED
        if exc.error_type == "daily_quota_exceeded":
            raise  # caller catches this specifically for sys.exit
    except resend.exceptions.ResendError:
        record.status = Status.SEND_FAILED

    return record
```

### Pattern 2: log_record() Function

**What:** Opens the CSV in append mode, writes the header if the file is new, writes one row, and flushes immediately. Uses `CompanyRecord.to_csv_row()` directly.

**When to use:** Immediately after every company attempt — success, failure, or rate limit — before advancing the loop.

**Example:**
```python
# Source: Python stdlib csv module; pathlib.Path
import csv
from pathlib import Path

from job_mailer.models import CompanyRecord

_LOG_FIELDNAMES = [
    "url", "company_name", "email_found", "generated_message",
    "status", "resend_message_id", "timestamp",
]


def log_record(record: CompanyRecord, log_path: str = "outreach_log.csv") -> None:
    """Append one record to the CSV log. Creates file with header if absent."""
    path = Path(log_path)
    write_header = not path.exists()
    with open(path, mode="a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_LOG_FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(record.to_csv_row())
        fh.flush()
```

### Pattern 3: Main Loop Integration

**What:** The `__main__.py` loop is extended with send delay, send+log calls, and a run summary counter.

**Example:**
```python
# Source: CONTEXT.md decisions
import time
import sys

sent_count = 0
failed_count = 0
no_email_count = 0
delay = profile.get("send", {}).get("delay_seconds", 2)

for row in reader:
    # ... scrape, generate (existing) ...
    if record.generated_message:
        try:
            record = send_email(record, profile)
        except resend.exceptions.RateLimitError:
            # daily_quota_exceeded: log then abort
            record.status = Status.RATE_LIMITED
            log_record(record)
            typer.echo(
                f"ERROR: Resend daily quota exceeded. Sent {sent_count} emails this run. "
                f"Remaining companies not processed.",
                err=True,
            )
            sys.exit(1)
        log_record(record)
        if record.status == Status.SENT:
            typer.echo(f"  {record.company_name} — {record.email_found} — sent")
            sent_count += 1
        elif record.status == Status.RATE_LIMITED:
            typer.echo(f"  WARNING: {record.company_name} — rate_limited (429)", err=True)
            failed_count += 1
        else:
            failed_count += 1
    else:
        no_email_count += 1
        log_record(record)  # log skipped/failed records too
    time.sleep(delay)

typer.echo(f"Done. {sent_count} sent, {failed_count} failed, {no_email_count} no email found.")
```

### Anti-Patterns to Avoid

- **Inspecting HTTP status code instead of error_type:** `exc.code == 429` does not distinguish `daily_quota_exceeded` from `rate_limit_exceeded`. Always use `exc.error_type`.
- **Catching bare `Exception`:** This hides bugs. Catch `resend.exceptions.ResendError` as the catch-all for Resend errors; let other exceptions propagate.
- **Opening the log file once for the entire run in write mode:** This truncates previous runs. Always open in append mode (`mode="a"`).
- **Writing the header every time:** Results in duplicate headers mid-file. Only write header when `not Path(log_path).exists()`.
- **Delaying before logging:** The delay must be placed after logging, not before. LOG-01 requires the record to be written immediately after the attempt.
- **Raising inside send_email() for expected errors:** The established pattern (scraper, generator) is to return a populated record with an error status, not to raise. Only `daily_quota_exceeded` is a special case that exits (re-raise so caller handles).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Email sending | Custom `httpx` POST to Resend API | `resend.Emails.send()` | SDK handles auth headers, JSON serialisation, HTTP error-to-exception mapping, and error_type extraction from `"name"` field |
| Error type discrimination | Parse response JSON manually | `exc.error_type` on caught `resend.exceptions.RateLimitError` | SDK already maps `response["name"]` -> `error_type`; no manual JSON needed |
| CSV writing | Manual string concatenation | `csv.DictWriter` | Handles quoting, newlines, and field ordering correctly |

**Key insight:** The Resend SDK already does the hard work of reading the `"name"` field from API response JSON and surfacing it as `exc.error_type`. Never parse the raw HTTP response manually.

---

## Common Pitfalls

### Pitfall 1: Confusing RateLimitError Subtypes
**What goes wrong:** Both `rate_limit_exceeded` (per-second) and `daily_quota_exceeded` raise `resend.exceptions.RateLimitError`. Code that catches `RateLimitError` without inspecting `.error_type` cannot distinguish them.
**Why it happens:** The SDK uses one exception class for all three 429 variants. Looking only at the exception type is insufficient.
**How to avoid:** After catching `RateLimitError`, check `exc.error_type == "daily_quota_exceeded"` before deciding whether to abort the run or log and continue.
**Warning signs:** Run aborts after every 429 response, not just quota exhaustion.

### Pitfall 2: CSV Header Written on Every Run
**What goes wrong:** If the log file exists from a prior run, writing the header again creates a duplicate header row mid-file. CSV parsers may treat subsequent data rows as malformed.
**Why it happens:** `open(path, "a")` does not truncate but also does not know whether a header already exists.
**How to avoid:** `write_header = not Path(log_path).exists()` before opening. Write header only when `write_header` is True.
**Warning signs:** `outreach_log.csv` has `url,company_name,...` appearing as a data row partway through the file.

### Pitfall 3: Log Written After Loop Ends (Not Per-Row)
**What goes wrong:** If the program crashes mid-run, no records from the current run appear in the log.
**Why it happens:** Batching writes for efficiency. LOG-01 explicitly forbids this.
**How to avoid:** Call `log_record(record)` inside the loop body, before `time.sleep()`. Call `fh.flush()` inside `log_record()`.
**Warning signs:** Log file is empty or only contains the previous run's records after an interrupted run.

### Pitfall 4: send_email() Raising on Expected Failures
**What goes wrong:** `SEND_FAILED` cases propagate as exceptions to `__main__.py`, breaking the per-row exception contract and triggering the outer `except Exception` catch that swallows context.
**Why it happens:** Not following the established "return record with status" pattern from scraper.py and generator.py.
**How to avoid:** Catch all `resend.exceptions.ResendError` subclasses inside `send_email()`. Return the record. Only re-raise `RateLimitError` when `error_type == "daily_quota_exceeded"` so the caller can execute the abort+exit path.

### Pitfall 5: Missing RATE_LIMITED from Status Enum
**What goes wrong:** `Status.RATE_LIMITED` used in `send_email()` before it is added to the enum raises `AttributeError`.
**Why it happens:** The enum in `models.py` must be extended before `sender.py` can reference it.
**How to avoid:** Add `RATE_LIMITED = "rate_limited"` to `Status` in `models.py` as the first task in Wave 0.

### Pitfall 6: invalid_email Is a ValidationError, Not a RateLimitError
**What goes wrong:** Code that only catches `RateLimitError` misses `invalid_from_address` and similar 422 errors, which propagate as unhandled exceptions.
**Why it happens:** The CONTEXT.md decision maps invalid email -> `send_failed`, but this comes from a `ValidationError` (HTTP 422) or `MissingRequiredFieldsError`, not a `RateLimitError`.
**How to avoid:** The catch-all `except resend.exceptions.ResendError` inside `send_email()` covers all non-RateLimitError SDK exceptions. No special-casing of `invalid_email` is needed in the exception hierarchy — it falls through to the catch-all.

---

## Code Examples

Verified patterns from installed resend package (version >=2.23.0, inspected 2026-03-15):

### Sending an Email
```python
# Source: resend.Emails.SendParams TypedDict; resend.Emails.SendResponse
import os
import resend

resend.api_key = os.environ["RESEND_API_KEY"]

params: resend.Emails.SendParams = {
    "from": os.environ["RESEND_FROM_EMAIL"],
    "to": ["recipient@example.com"],
    "subject": "Subject line",
    "text": "Plain text email body",
}

response = resend.Emails.send(params)
message_id: str = response.id  # e.g. "re_123abc..."
```

### Exception Hierarchy (from resend.exceptions source)
```python
# All exceptions live in resend.exceptions
# Hierarchy:
#   Exception
#     resend.exceptions.ResendError          (base — all Resend API errors)
#       resend.exceptions.ValidationError    (400, 422)
#       resend.exceptions.MissingRequiredFieldsError (422)
#       resend.exceptions.MissingApiKeyError (401)
#       resend.exceptions.InvalidApiKeyError (403)
#       resend.exceptions.RateLimitError     (429 — rate_limit_exceeded, daily_quota_exceeded, monthly_quota_exceeded)
#       resend.exceptions.ApplicationError   (500)
#     resend.exceptions.NoContentError       (empty response body)

# Key attribute on ResendError:
#   exc.error_type  -> str, maps to API response "name" field
#   exc.code        -> str|int, HTTP status code
#   exc.message     -> str, human-readable description
```

### Discriminating daily_quota_exceeded from rate_limit_exceeded
```python
# Source: resend.exceptions.ERRORS dict (inspected 2026-03-15)
import resend.exceptions

try:
    response = resend.Emails.send(params)
except resend.exceptions.RateLimitError as exc:
    if exc.error_type == "daily_quota_exceeded":
        # Abort the entire run — quota exhausted
        pass
    else:
        # Per-second rate limit — log and continue
        pass
except resend.exceptions.ResendError:
    # All other Resend errors (ValidationError, ApplicationError, etc.)
    pass
```

### Reading send delay from profile
```python
# Source: profile.example.toml [send] section
delay: int = profile.get("send", {}).get("delay_seconds", 2)
time.sleep(delay)
```

### CSV append-mode logging with header guard
```python
# Source: Python stdlib csv; pathlib.Path
import csv
from pathlib import Path

_FIELDNAMES = [
    "url", "company_name", "email_found", "generated_message",
    "status", "resend_message_id", "timestamp",
]

def log_record(record: CompanyRecord, log_path: str = "outreach_log.csv") -> None:
    path = Path(log_path)
    write_header = not path.exists()
    with open(path, mode="a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(record.to_csv_row())
        fh.flush()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Inspect HTTP status code for error type | Inspect `exc.error_type` (maps to API `"name"` field) | Resend Python SDK 2.0 (2024) | Must not use `exc.code == 429` alone — use `exc.error_type` to distinguish subtypes |
| `resend.Emails.send()` returns dict | Returns typed `SendResponse` with `.id` attribute | SDK 2.0 redesign | Access `response.id` not `response["id"]` |

**Deprecated/outdated:**
- `resend.Emails.send()` returning a plain dict: replaced by `SendResponse` TypedDict-like object in SDK 2.0. Access `.id` as an attribute.

---

## Open Questions

1. **invalid_email error_type string**
   - What we know: The Resend error docs list `invalid_from_address` (422) as the error name for bad from-address. There is no `invalid_email` error code in the official docs.
   - What's unclear: The CONTEXT.md references `invalid_email` as a Resend error type, but the API docs show `invalid_from_address`. These may refer to the same error with different names, or the `invalid_email` label may refer to an `to` recipient address validation failure surfaced differently.
   - Recommendation: At implementation time, test with a malformed `to` address and log `exc.error_type` to confirm the actual string. The catch-all `except resend.exceptions.ResendError -> status=send_failed` handles this correctly regardless of the exact error_type string — no special-casing is needed in code.

2. **Race condition on CSV header check**
   - What we know: `write_header = not Path(log_path).exists()` followed by `open(mode="a")` has a TOCTOU gap.
   - What's unclear: Whether this matters in practice for a single-process CLI tool.
   - Recommendation: For a single-process CLI (no parallelism), this is a non-issue. Document as a known limitation.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (from pyproject.toml dev dependencies) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — testpaths=["tests"], addopts="-x" |
| Quick run command | `uv run pytest tests/test_sender.py tests/test_logger.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEND-01 | `send_email()` calls `resend.Emails.send()` with correct params and sets `record.status = Status.SENT` and `record.resend_message_id` on success | unit | `uv run pytest tests/test_sender.py::test_send_success -x` | Wave 0 |
| SEND-02 | `send_email()` catches `RateLimitError` with `error_type="rate_limit_exceeded"` and sets `Status.RATE_LIMITED`; run continues | unit | `uv run pytest tests/test_sender.py::test_rate_limit_continues -x` | Wave 0 |
| SEND-02 | `send_email()` catches `RateLimitError` with `error_type="daily_quota_exceeded"` and re-raises; `__main__` logs and exits | unit | `uv run pytest tests/test_sender.py::test_daily_quota_reraises -x` | Wave 0 |
| SEND-02 | `send_email()` catches `ResendError` (non-429) and sets `Status.SEND_FAILED` | unit | `uv run pytest tests/test_sender.py::test_send_failed_non_429 -x` | Wave 0 |
| SEND-03 | `__main__` reads `profile["send"]["delay_seconds"]` and calls `time.sleep(delay)` between rows | unit | `uv run pytest tests/test_cli.py::test_send_delay_called -x` | Wave 0 |
| LOG-01 | `log_record()` writes one row immediately; file exists after first call | unit | `uv run pytest tests/test_logger.py::test_log_written_immediately -x` | Wave 0 |
| LOG-01 | `log_record()` appends a second row without truncating the first | unit | `uv run pytest tests/test_logger.py::test_log_appends -x` | Wave 0 |
| LOG-02 | Logged row contains all 7 fields with correct values | unit | `uv run pytest tests/test_logger.py::test_log_fields -x` | Wave 0 |
| LOG-02 | CSV header is written only on file creation, not on subsequent appends | unit | `uv run pytest tests/test_logger.py::test_header_written_once -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_sender.py tests/test_logger.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_sender.py` — covers SEND-01, SEND-02 (all error branches)
- [ ] `tests/test_logger.py` — covers LOG-01, LOG-02
- [ ] `models.py` update: `Status.RATE_LIMITED = "rate_limited"` must exist before RED test import works

*(No new test infrastructure needed — pytest + unittest.mock covers all patterns; resend SDK calls mocked with `unittest.mock.patch`)*

---

## Sources

### Primary (HIGH confidence)
- `resend.exceptions` source code — inspected via `uv run python -c "import inspect; import resend.exceptions; print(inspect.getsource(resend.exceptions))"` from installed resend>=2.23.0 — exception class hierarchy, `ERRORS` dict, `error_type` attribute, `raise_for_code_and_type` logic
- `resend.Emails.SendResponse` source — inspected from installed package — confirms `.id` is the attribute name for the sent email ID
- `profile.example.toml` — confirms `[send] delay_seconds = 2` is the existing schema for delay configuration
- `src/job_mailer/models.py` — confirms `Status.SEND_FAILED` exists; `RATE_LIMITED` does not yet exist; `to_csv_row()` returns all 7 LOG-02 fields
- `src/job_mailer/__main__.py` — confirms existing loop structure and integration points
- Python stdlib `csv.DictWriter` — standard, well-understood

### Secondary (MEDIUM confidence)
- https://resend.com/docs/api-reference/errors — official error code table; confirmed `daily_quota_exceeded`, `rate_limit_exceeded`, `monthly_quota_exceeded` are distinct `"name"` values all mapping to HTTP 429
- `resend.request` source (via WebFetch) — confirms `error_type=data.get("name", "InternalServerError")` mapping from API response JSON field `"name"` to exception `error_type` attribute

### Tertiary (LOW confidence)
- `invalid_email` as an exact Resend error_type string — not confirmed in official docs (docs show `invalid_from_address`); catch-all handles it regardless

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — resend library already in pyproject.toml; inspected from installed package
- Architecture: HIGH — follows established scraper/generator patterns exactly; integration points confirmed from __main__.py source
- Error discrimination: HIGH — exception source code inspected directly from installed package
- CSV logging: HIGH — stdlib csv.DictWriter, well-understood pattern
- Pitfalls: HIGH — derived from source inspection and API docs, not speculation

**Research date:** 2026-03-15
**Valid until:** 2026-06-15 (resend SDK is stable; API error codes are stable)
