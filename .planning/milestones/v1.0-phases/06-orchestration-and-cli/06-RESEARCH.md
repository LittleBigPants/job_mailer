# Phase 6: Orchestration and CLI - Research

**Researched:** 2026-03-15
**Domain:** Python CLI (Typer), CSV I/O, pipeline orchestration
**Confidence:** HIGH

## Summary

Phase 6 is a surgical modification to a single file (`__main__.py`) plus a one-line addition to `models.py`. The pipeline itself — scrape, generate, send, log, delay — is fully implemented and tested. What remains is wiring two safety features around that loop: `--dry-run` mode and idempotent re-runs. All required libraries (Typer, csv, pathlib) are already in place and their patterns are established across the existing codebase.

No new dependencies are introduced. The implementation risk is low because the control flow branches are well-defined by CONTEXT.md decisions and all supporting infrastructure (Status enum, `log_record()`, `CompanyRecord.to_csv_row()`) is already present and working.

The one non-obvious design point is the idempotency loader: it must read `outreach_log.csv` at startup using `csv.DictReader` and build a `set[str]` of URLs where `status == "sent"`. This set is checked before entering the per-row pipeline. A second `set[str]` tracks URLs seen within the current run to handle duplicate rows in the input CSV.

**Primary recommendation:** Modify `__main__.py` to add two Typer options (`--dry-run`, `--delay`), load the sent-URL set from the existing log at startup, then branch the per-row logic on `dry_run`. Add `DRY_RUN = "dry_run"` to the `Status` enum in `models.py`.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Dry-run logging:**
- Log entries ARE written for dry-run rows — status value: `dry_run` (needs `DRY_RUN` added to `Status` enum)
- Terminal output per company: `[DRY RUN] {company_name} — {email_found} — {first N chars of generated_message}`
- Idempotency applies in dry-run mode — already-sent URLs are still skipped even during `--dry-run`
- Run summary uses a distinct prefix: `Done (dry run). X would send, Y failed, Z no email found.`

**Idempotency scope:**
- Only `status=sent` triggers a skip on re-run — failed, rate-limited, and dry-run entries are retried
- Deduplicate within the same run: if the same URL appears multiple times in the input CSV, only the first occurrence is processed; subsequent occurrences are silently skipped
- No terminal output for skipped rows — silent skip only
- Run summary includes a skipped count: `Done. X sent, Y skipped, Z failed, W no email found.`

**--delay CLI flag:**
- `--delay` on the CLI overrides `profile.toml`'s `delay_seconds` — CLI flag wins
- Default: 2 seconds when neither `--delay` nor `profile.toml` `delay_seconds` is set
- Integer only — no fractional seconds (Typer `int` type)
- Priority order: `--delay` CLI flag > `profile.toml` `delay_seconds` > hardcoded default of 2

### Claude's Discretion

- Message preview length for `[DRY RUN]` output (e.g. first 80 chars, truncated with `...`)
- How to load the existing log for idempotency check at startup (read into a set of sent URLs)
- Whether to add `DRY_RUN` to Status enum as `"dry_run"` string value

### Deferred Ideas (OUT OF SCOPE)

- `--log` flag for configurable log file path
- `--limit N` flag (SAFE-01, v2)
- `--preview` flag (UX-01, v2)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SEND-04 | `--dry-run` flag causes the tool to scrape and generate messages but never call the Resend API | Typer `bool` option with `is_flag=True`; branch in per-row logic skips `send_email()` call; records logged with `Status.DRY_RUN` |
| LOG-03 | On re-run, URLs where `status=sent` in the existing log are skipped (idempotent re-runs) | `csv.DictReader` on `outreach_log.csv` at startup; filter rows where `status == "sent"`; collect `url` values into `set[str]`; check membership before entering pipeline |
</phase_requirements>

---

## Standard Stack

### Core (all already installed)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| typer | >=0.24.1 | CLI option parsing (`--dry-run`, `--delay`) | Installed, in use |
| csv (stdlib) | 3.11+ | `DictReader` for idempotency log load | Installed, in use |
| pathlib (stdlib) | 3.11+ | Log file existence check | Installed, in use |

### No New Dependencies

Phase 6 introduces zero new packages. All required tools are in the existing project.

## Architecture Patterns

### Existing Project Structure (unchanged)

```
src/job_mailer/
├── __main__.py     # MODIFIED: add --dry-run, --delay options; idempotency loader; dry-run branch
├── models.py       # MODIFIED: add Status.DRY_RUN = "dry_run"
├── config.py       # unchanged
├── scraper.py      # unchanged
├── generator.py    # unchanged
├── sender.py       # unchanged
└── logger.py       # unchanged
```

### Pattern 1: Typer Optional Int with None Default

The `--delay` flag must be optional so `None` can distinguish "not provided on CLI" from "provided as 0". The priority chain is: CLI value → profile.toml value → hardcoded 2.

```python
# Source: Typer docs — Optional parameters with default None
@app.command()
def main(
    input: Path = typer.Option(..., "--input", exists=True, readable=True, file_okay=True, dir_okay=False),
    dry_run: bool = typer.Option(False, "--dry-run", help="Scrape and generate but do not send."),
    delay: Optional[int] = typer.Option(None, "--delay", help="Seconds between sends (overrides profile.toml)."),
) -> None:
    ...
    effective_delay = delay if delay is not None else profile.get("send", {}).get("delay_seconds", 2)
```

### Pattern 2: Idempotency Set Loaded at Startup

Load before the CSV loop. The log file may not exist on first run — guard with `Path.exists()`.

```python
# Pattern: load sent URLs into a set before the main loop
log_path = "outreach_log.csv"
already_sent: set[str] = set()
if Path(log_path).exists():
    with open(log_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("status") == "sent":
                already_sent.add(row["url"])
```

### Pattern 3: Within-Run Deduplication Set

Maintain a second set that grows as the loop processes rows. Check it before the idempotency check so both share the same skip path (silent, no output).

```python
seen_urls: set[str] = set()
# Inside the loop, before any processing:
if url in already_sent or url in seen_urls:
    seen_urls.add(url)   # still add so second occurrence is also deduplicated
    skipped_count += 1
    continue
seen_urls.add(url)
```

Note: The CONTEXT.md says skipped rows have no terminal output — `continue` without any `typer.echo`.

### Pattern 4: Dry-Run Branch

The dry-run branch replaces the `send_email()` call with a status assignment and preview echo. All other steps (scrape, generate, log) remain identical.

```python
if dry_run:
    record.status = Status.DRY_RUN
    preview = (record.generated_message[:80] + "...") if len(record.generated_message) > 80 else record.generated_message
    typer.echo(f"[DRY RUN] {record.company_name} — {record.email_found} — {preview}")
    log_record(record)
    would_send_count += 1
else:
    # existing send_email() + log_record() path
    ...
```

### Pattern 5: Dual Summary Lines

Real run: `Done. X sent, Y skipped, Z failed, W no email found.`
Dry run: `Done (dry run). X would send, Y failed, Z no email found.`

The dry-run summary omits the skipped count (CONTEXT.md does not include it in that format). Track separate counters: `sent_count`/`would_send_count`, `skipped_count`, `failed_count`, `no_email_count`.

### Anti-Patterns to Avoid

- **Skipping the log write in dry-run mode:** CONTEXT.md is explicit — dry-run rows ARE logged with `status=dry_run`.
- **Using `status=skipped` for cross-run idempotency:** `Status.SKIPPED` is for within-run deduplication. Already-sent URLs from a previous run are also counted as `skipped_count` in the summary, but no new log row is written for them (they're just `continue`-d).
- **Applying idempotency only in live mode:** CONTEXT.md states "idempotency applies in dry-run mode — already-sent URLs are still skipped even during `--dry-run`".
- **Reading the log inside the per-row loop:** Load the sent-URL set once at startup, before the loop. Reading the file per-row is wasteful and races with the append happening inside the loop.
- **Using `Optional[int]` without `from __future__ import annotations` or `typing.Optional`:** The file already has `from __future__ import annotations` so `Optional[int]` can be written as `int | None` in the type hint.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI option parsing | Custom argparse wrapper | Typer (already in use) | Typer handles type coercion, help text, exists validation — all working |
| CSV reading for idempotency | Manual line splitting | `csv.DictReader` | Handles quoted fields, encoding correctly; already used in `__main__.py` |
| Log existence check | `try/open` with exception | `Path.exists()` | Already the established pattern in `logger.py` |

## Common Pitfalls

### Pitfall 1: Skipped Count Semantics

**What goes wrong:** Both within-run duplicates and already-sent URLs are silently skipped. If the planner uses two different counters for these, the summary becomes wrong. If it uses one counter, it needs to capture both cases.

**Why it happens:** CONTEXT.md summary format shows one `Y skipped` bucket, but there are two skip triggers.

**How to avoid:** Use a single `skipped_count` incremented by both the `url in already_sent` and `url in seen_urls` branches. Both are silent (no echo), both increment the same counter.

**Warning signs:** Summary shows 0 skipped even when a CSV contains duplicates or re-runs against an existing log.

### Pitfall 2: Dry-Run Record Gets `status=sent` from Existing send_email() Flow

**What goes wrong:** If the dry-run branch is placed incorrectly (after `send_email()` is called), `Status.DRY_RUN` is never set.

**Why it happens:** The existing `record = send_email(record, profile)` line overwrites `record.status`.

**How to avoid:** The dry-run branch must replace the `send_email()` call entirely, not wrap around it. The `if dry_run: ... else: send_email(...)` structure must be mutually exclusive.

### Pitfall 3: Delay Priority Chain Off-by-One

**What goes wrong:** `delay if delay else profile_delay` evaluates `delay=0` as falsy, breaking the priority chain.

**Why it happens:** `0` is falsy in Python.

**How to avoid:** Use `delay if delay is not None else ...`. The CONTEXT.md specifies integer only and default 2, so `delay=0` is semantically valid (no delay), even if unusual.

### Pitfall 4: Log Read Races with Log Write

**What goes wrong:** If the idempotency set is rebuilt from the log every iteration, rows written in the current run could interfere with the re-run check logic.

**Why it happens:** `log_record()` appends to the file inside the loop.

**How to avoid:** Read the log once into `already_sent` before the loop starts. `already_sent` remains static for the duration of the run. New entries in the current run do not affect skip decisions for other rows in the same run (that is handled by `seen_urls`).

### Pitfall 5: Test Patching of `time` Module

**What goes wrong:** Existing tests patch `job_mailer.__main__.time` as a module object. Adding `--delay` to the signature changes how `time.sleep(effective_delay)` is called, so the `mock_time.sleep.assert_called_once_with(N)` assertion value must match `effective_delay`, not the old `profile.get(...)` chain.

**How to avoid:** Update `test_send_delay_called` to pass `--delay 3` and assert `mock_time.sleep.assert_called_once_with(3)`, or patch `load_profile` to return a profile with `delay_seconds=3` and assert the same. Both paths are valid — the test already patches `load_profile`.

## Code Examples

### Adding `--dry-run` as a Typer bool flag

```python
# Source: Typer documentation — boolean flags
dry_run: bool = typer.Option(False, "--dry-run", help="Scrape and generate but do not send.")
```

Typer maps `--dry-run` to `dry_run=True` automatically. No `is_flag=True` needed with the bool type.

### Adding `--delay` as an optional int

```python
# Source: Typer documentation — optional parameters
from typing import Optional

delay: Optional[int] = typer.Option(None, "--delay", help="Seconds to wait between sends.")
```

Then resolve in function body:

```python
effective_delay = delay if delay is not None else profile.get("send", {}).get("delay_seconds", 2)
```

### Loading the idempotency set

```python
# Pattern from existing logger.py + csv stdlib
import csv
from pathlib import Path

log_path = "outreach_log.csv"
already_sent: set[str] = set()
if Path(log_path).exists():
    with open(log_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("status") == "sent":
                already_sent.add(row["url"])
```

### Adding Status.DRY_RUN to the enum

```python
# In models.py — Status enum already inherits from str+enum.Enum
class Status(str, enum.Enum):
    ...
    DRY_RUN = "dry_run"
```

Because the enum inherits `str`, `Status.DRY_RUN == "dry_run"` is `True` without `.value`. The `to_csv_row()` method calls `self.status.value` explicitly, so the CSV will contain the string `"dry_run"`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No dry-run safety | `--dry-run` flag skips Resend API calls | Phase 6 | Prevents accidental sends during testing |
| No idempotency | Skip `status=sent` URLs on re-run | Phase 6 | Safe to re-run against same CSV |
| Delay from profile only | `--delay` CLI flag overrides profile | Phase 6 | One-shot override without editing config |

## Open Questions

1. **Preview truncation length for `[DRY RUN]` output**
   - What we know: CONTEXT.md says "first N chars of generated_message" and lists 80 chars as an example
   - What's unclear: Exact value is left to Claude's Discretion
   - Recommendation: 80 characters with trailing `...` if truncated — matches CONTEXT.md example, long enough to distinguish messages, short enough for terminal readability

2. **Whether already-sent skips write a new log row**
   - What we know: CONTEXT.md says "silent skip only" with no terminal output
   - What's unclear: Whether a `status=skipped` row should be appended for cross-run skips
   - Recommendation: Do NOT write a log row for cross-run skips. The original `status=sent` row already exists in the log; writing a second row would create ambiguity. Within-run duplicate skips also should not be logged — both are silent continues.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (installed via `[dependency-groups] dev`) |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` testpaths=["tests"], addopts="-x" |
| Quick run command | `uv run pytest tests/test_cli.py -x` |
| Full suite command | `uv run pytest -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEND-04 | `--dry-run` prevents `send_email()` from being called | unit | `uv run pytest tests/test_cli.py::test_dry_run_does_not_call_send_email -x` | ❌ Wave 0 |
| SEND-04 | `--dry-run` writes log row with `status=dry_run` | unit | `uv run pytest tests/test_cli.py::test_dry_run_logs_dry_run_status -x` | ❌ Wave 0 |
| SEND-04 | `--dry-run` prints `[DRY RUN]` prefix to stdout | unit | `uv run pytest tests/test_cli.py::test_dry_run_terminal_output -x` | ❌ Wave 0 |
| SEND-04 | `--dry-run` summary line uses `Done (dry run). X would send...` | unit | `uv run pytest tests/test_cli.py::test_dry_run_summary_line -x` | ❌ Wave 0 |
| LOG-03 | Already-sent URL is silently skipped on re-run | unit | `uv run pytest tests/test_cli.py::test_idempotency_skips_sent_url -x` | ❌ Wave 0 |
| LOG-03 | Skipped URL does not call `send_email()` | unit | `uv run pytest tests/test_cli.py::test_idempotency_no_send_for_skipped -x` | ❌ Wave 0 |
| LOG-03 | Duplicate URL in same CSV: second occurrence silently skipped | unit | `uv run pytest tests/test_cli.py::test_within_run_dedup -x` | ❌ Wave 0 |
| LOG-03 | `--dry-run` still skips already-sent URLs | unit | `uv run pytest tests/test_cli.py::test_dry_run_respects_idempotency -x` | ❌ Wave 0 |
| SEND-03 | `--delay` CLI flag overrides `profile.toml` delay_seconds | unit | `uv run pytest tests/test_cli.py::test_cli_delay_flag_overrides_profile -x` | ❌ Wave 0 |
| SEND-03 | Default delay is 2 when neither `--delay` nor profile delay set | unit | `uv run pytest tests/test_cli.py::test_cli_delay_default_is_2 -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_cli.py -x`
- **Per wave merge:** `uv run pytest -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_cli.py` — all 10 test functions listed above (file exists but needs Phase 6 tests appended)
- [ ] No new framework install needed — pytest is already installed

## Sources

### Primary (HIGH confidence)

- Direct code inspection of `src/job_mailer/__main__.py` — current pipeline implementation, existing counter and delay patterns
- Direct code inspection of `src/job_mailer/models.py` — Status enum and existing values
- Direct code inspection of `src/job_mailer/logger.py` — log_record() signature, log path default, csv field list
- Direct code inspection of `tests/test_cli.py` — existing test patterns (patch targets, CliRunner usage, fixture shape)
- `.planning/phases/06-orchestration-and-cli/06-CONTEXT.md` — all locked decisions
- Python 3.11 stdlib csv.DictReader — well-documented, no version ambiguity
- Typer 0.24.x — bool options and Optional[int] patterns consistent with installed version

### Secondary (MEDIUM confidence)

- Typer documentation on boolean flags — behavior of `bool` type with `--flag` naming convention confirmed consistent with existing `exists=True` pattern used in `--input`

### Tertiary (LOW confidence)

None — all findings are based on direct code inspection or stdlib documentation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies; all libraries are installed and actively used
- Architecture: HIGH — control flow is fully specified by CONTEXT.md decisions; code patterns are directly observable
- Pitfalls: HIGH — derived from direct code reading (existing test patch targets, enum inheritance behavior, delay resolution)

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable — no external APIs or fast-moving libraries involved)
