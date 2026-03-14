# Architecture Research

**Domain:** Python CLI batch pipeline tool (scrape → generate → send → log)
**Researched:** 2026-03-14
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Entry Point                           │
│              (Typer/Click command with --dry-run flag)           │
├─────────────────────────────────────────────────────────────────┤
│                       Pipeline Orchestrator                      │
│         Reads config + CSV, drives per-row processing loop       │
├──────────┬──────────────┬──────────────┬────────────────────────┤
│  Scraper │   Generator  │   Sender     │       Logger           │
│          │              │              │                        │
│ HTTP GET │ Groq API     │ Resend API   │ Append-only CSV/JSONL  │
│ email    │ personalized │ sends email  │ per-row outcome        │
│ harvest  │ intro text   │ (skipped if  │ (url, email, status,   │
│          │              │  dry_run)    │  msg_id, timestamp)    │
├──────────┴──────────────┴──────────────┴────────────────────────┤
│                        Shared Models                             │
│        CompanyRecord dataclass — flows through all stages        │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `cli.py` | Parse flags (`--dry-run`, `--input`, `--delay`), load config, invoke orchestrator | Typer app with typed function signature |
| `orchestrator.py` | Read CSV, loop rows, call stage functions in order, enforce delay, handle per-row exceptions | Plain Python; drives the pipeline |
| `scraper.py` | Fetch homepage → /contact → /about; extract first `mailto:` or `href` email | `httpx` or `requests`, `BeautifulSoup` |
| `generator.py` | Build prompt from CompanyRecord + developer profile, call Groq API, return message text | `groq` SDK; prompt template lives here |
| `sender.py` | Call Resend API with to/subject/body; return message_id | `resend` SDK; no-ops in dry_run mode |
| `logger.py` | Append one row to the log CSV per processed company | `csv.DictWriter` in append mode |
| `models.py` | `CompanyRecord` dataclass — shared data structure across all stages | `@dataclass` with typed fields |
| `config.py` | Load and validate `profile.toml`; expose typed `ProfileConfig` object | `tomllib` (stdlib Python 3.11+) |

## Recommended Project Structure

```
job_mailer/
├── __init__.py
├── cli.py               # Typer entry point; flags, --dry-run
├── orchestrator.py      # Pipeline loop; row-by-row control flow
├── scraper.py           # HTTP fetch + email extraction
├── generator.py         # Groq API prompt + LLM call
├── sender.py            # Resend API call (no-op in dry_run)
├── logger.py            # Append-only CSV log writer
├── models.py            # CompanyRecord dataclass
└── config.py            # profile.toml loader
profile.toml             # Developer profile (gitignored or committed)
companies.csv            # Input: single-column list of URLs
log.csv                  # Output: append-only run log
pyproject.toml           # Dependencies and CLI entry point script
```

### Structure Rationale

- **One file per pipeline stage:** Each stage is independently testable and replaceable. Scraper changes do not touch generator logic.
- **`models.py` as the contract:** `CompanyRecord` is the shared data type. All stages accept or return it; this prevents implicit coupling through dict passing.
- **`orchestrator.py` owns the loop:** The CLI entry point stays thin. Business logic (retry, delay, skip already-sent rows) lives in the orchestrator, not scattered across commands.
- **`config.py` separate from `cli.py`:** Keeps config loading testable without invoking Click/Typer machinery.

## Architectural Patterns

### Pattern 1: Linear Stage Pipeline with a Shared Record

**What:** A single `CompanyRecord` dataclass is created at the start of each row's processing and is progressively enriched as it passes through scraper → generator → sender. Each stage mutates or returns an updated version of the record.

**When to use:** Exactly this scenario — a fixed, ordered sequence of operations on a single entity per row.

**Trade-offs:** Simple and predictable. Cannot parallelize stages for the same row. Straightforward to test each stage in isolation by constructing a `CompanyRecord` directly.

**Example:**
```python
# models.py
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class CompanyRecord:
    url: str
    company_name: str = ""
    email_found: str = ""
    generated_message: str = ""
    status: str = "pending"           # pending | sent | dry_run | no_email | error
    resend_message_id: str = ""
    error_detail: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
```

### Pattern 2: Continue-on-Error with Per-Row Exception Handling

**What:** The pipeline loop wraps each row's full processing in a try/except. A failed row (scrape timeout, API error, etc.) logs its failure status and continues to the next row. The batch never aborts early.

**When to use:** Any batch operation where partial success is acceptable and retrying later is possible. Critical for this tool — a Groq rate limit on row 7 should not lose rows 8–50.

**Trade-offs:** Requires explicit status tracking so errors are visible in the log. Slightly more code in the loop, but much more robust in production.

**Example:**
```python
# orchestrator.py
for row in rows:
    record = CompanyRecord(url=row["url"], company_name=derive_name(row["url"]))
    try:
        record = scraper.extract_email(record)
        if not record.email_found:
            record.status = "no_email"
        else:
            record = generator.generate_message(record, profile)
            if not dry_run:
                record = sender.send(record)
            else:
                record.status = "dry_run"
    except Exception as exc:
        record.status = "error"
        record.error_detail = str(exc)
    finally:
        logger.append(record)
    time.sleep(delay)
```

### Pattern 3: Append-Only Log as State Store

**What:** Every row outcome is written to an append-only log CSV after processing, regardless of success or failure. On re-run, the orchestrator reads the existing log and skips URLs that already have `status=sent`.

**When to use:** Personal batch tools without a database. The log file becomes both the audit trail and the resumability mechanism.

**Trade-offs:** Simple to implement; human-readable. Not suitable for concurrent runs (no locking). For a personal tool running once at a time, this is the right tradeoff.

**Skip-already-sent check:**
```python
# orchestrator.py  — skip rows already successfully sent
sent_urls = {r["url"] for r in read_log() if r["status"] == "sent"}
rows_to_process = [r for r in input_rows if r["url"] not in sent_urls]
```

## Data Flow

### Pipeline Flow (per row)

```
companies.csv
    |
    v
[orchestrator] reads URL → CompanyRecord(url, company_name)
    |
    v
[scraper] GET homepage → /contact → /about
    |  extracts email address
    v
CompanyRecord.email_found populated
    |
    | (skip if no email found — log "no_email")
    v
[generator] builds prompt with record + profile.toml
    |  calls Groq API
    v
CompanyRecord.generated_message populated
    |
    | (skip actual send if --dry-run)
    v
[sender] calls Resend API
    |  receives message_id
    v
CompanyRecord.status = "sent", .resend_message_id populated
    |
    v
[logger] appends row to log.csv
    |
    v
time.sleep(delay)  →  next row
```

### Configuration Flow

```
profile.toml
    |
    v
[config.py] parse + validate → ProfileConfig object
    |
    v
passed into [generator] for prompt construction only
(not stored in CompanyRecord — it's static across rows)
```

### Resumability Flow

```
existing log.csv (may be empty on first run)
    |
    v
[orchestrator] reads sent URLs → builds skip set
    |
    v
input CSV rows filtered to exclude already-sent
    |
    v
pipeline runs on remaining rows only
```

## Suggested Build Order

Build in dependency order — each stage can be built and tested before wiring the next.

| Step | Component | Why This Order |
|------|-----------|----------------|
| 1 | `models.py` | No dependencies; defines the shared contract everything else uses |
| 2 | `config.py` | No external dependencies; enables profile loading for generator tests |
| 3 | `scraper.py` | Standalone HTTP logic; testable with real URLs or mocked responses |
| 4 | `generator.py` | Depends on `models.py` + `config.py`; testable with mock Groq responses |
| 5 | `sender.py` | Depends only on `models.py`; testable with mock Resend; thin wrapper |
| 6 | `logger.py` | Depends only on `models.py`; pure file I/O, easy to test |
| 7 | `orchestrator.py` | Wires all stages; integration test after all stages verified |
| 8 | `cli.py` | Thin wrapper around orchestrator; tested last as the public interface |

## Handling Partial Failures

| Failure Type | Behavior | Logged As |
|---|---|---|
| URL not reachable (timeout/5xx) | Continue to next row | `status=error`, `error_detail=<exception>` |
| No email found after all pages checked | Skip send and generate | `status=no_email` |
| Groq API error (rate limit, timeout) | Continue to next row | `status=error`, `error_detail=<exception>` |
| Resend API error (invalid email, etc.) | Continue to next row | `status=error`, `error_detail=<exception>` |
| --dry-run active | Skip send stage only | `status=dry_run` (message is generated) |

All failures are non-fatal. The log CSV captures everything. Re-running the tool skips `status=sent` rows only — `error` and `no_email` rows are retried.

## Anti-Patterns

### Anti-Pattern 1: Passing Dicts Between Stages

**What people do:** Use plain `dict` or `row` variables to carry data through the pipeline.
**Why it's wrong:** No type checking, keys are implicit contracts, easy to introduce typos or missing fields that only fail at runtime.
**Do this instead:** Define `CompanyRecord` as a `@dataclass` in `models.py` and pass it between every stage. Access is `record.email_found`, not `row["email_found"]`.

### Anti-Pattern 2: Business Logic in the CLI Entry Point

**What people do:** Put the processing loop, error handling, and API calls directly inside the Typer command function.
**Why it's wrong:** Makes the logic untestable without invoking the CLI. Mixing concerns means changing the delay behavior requires touching CLI code.
**Do this instead:** Keep `cli.py` to parsing arguments, loading config, and calling `orchestrator.run(...)`. All logic lives in the orchestrator and stage modules.

### Anti-Pattern 3: Aborting the Batch on Any Error

**What people do:** Let exceptions propagate out of the row loop, stopping processing entirely.
**Why it's wrong:** A single DNS failure or API rate limit at row 3 wastes all remaining rows. Re-running re-processes everything.
**Do this instead:** Wrap each row in try/except, log the error to the record, and continue. The batch always completes.

### Anti-Pattern 4: Storing State Only in Memory

**What people do:** Track sent companies in a Python set during the run; on crash or re-run, no memory of prior state.
**Why it's wrong:** Any interruption (Ctrl-C, crash, network drop) causes duplicate sends on re-run.
**Do this instead:** Append to the log file after every row. The log is the source of truth for what has been sent.

### Anti-Pattern 5: Hardcoding the Developer Profile

**What people do:** Embed name, stack, and links as constants in `generator.py` or the prompt string.
**Why it's wrong:** Updating the profile requires editing source code. Profile is user config, not code.
**Do this instead:** Load from `profile.toml` at runtime via `config.py`. The file lives outside the package.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Groq API | `groq` Python SDK; synchronous call in `generator.py` | Rate limits: handle 429 by logging error, not retrying in loop (re-run handles it) |
| Resend API | `resend` Python SDK; synchronous call in `sender.py` | Returns `message_id` on success; log it for delivery audit |
| Web pages | `httpx` (sync) + `BeautifulSoup`; `sender.py` | Set timeout (5–10s) and User-Agent; catch `httpx.RequestError` |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `orchestrator` → `scraper` | Direct function call, passes `CompanyRecord`, returns `CompanyRecord` | No shared state; pure function preferred |
| `orchestrator` → `generator` | Direct function call; also receives `ProfileConfig` | Generator does not import config directly |
| `orchestrator` → `sender` | Direct function call; `dry_run` flag passed in or checked inside sender | Sender returns updated record |
| `orchestrator` → `logger` | Direct function call; called in `finally` block to guarantee write | Logger opens file in append mode each call |
| `cli` → `orchestrator` | Single `run()` call with typed parameters | CLI does not know about stage implementations |

## Sources

- Simon Willison, "Things I've Learned About Building CLI Tools in Python" — https://simonwillison.net/2023/Sep/30/cli-tools-python/
- Click documentation (v8.3.x) — https://click.palletsprojects.com/
- BetterStack, "Creating Composable CLIs with Click" — https://betterstack.com/community/guides/scaling-python/click-explained/
- Start Data Engineering, "Data Pipeline Design Patterns #2: Coding Patterns in Python" — https://www.startdataengineering.com/post/code-patterns/
- Start Data Engineering, "How to Make Data Pipelines Idempotent" — https://www.startdataengineering.com/post/why-how-idempotent-data-pipeline/

---
*Architecture research for: Python CLI cold email outreach pipeline (job_mailer)*
*Researched: 2026-03-14*
