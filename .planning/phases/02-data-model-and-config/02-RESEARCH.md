# Phase 2: Data Model and Config - Research

**Researched:** 2026-03-14
**Domain:** Python dataclasses, CSV reading, Typer CLI argument parsing, profile validation
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INPUT-01 | Tool reads company URLs from a single-column CSV file specified via CLI argument | stdlib `csv` module for reading; `typer.Option` for `--input`; `CompanyRecord` dataclass as the row model; config validation must succeed before CSV is touched |
</phase_requirements>

---

## Summary

Phase 2 produces three deliverables that every downstream phase depends on: a `CompanyRecord` dataclass that is the shared row model for the entire pipeline, an extended `config.py` that validates required `profile.toml` fields at startup, and a stub CLI entry point that accepts `--input <csv>`, validates config, and exits cleanly.

The technical surface is narrow and entirely within the Python standard library plus the already-installed `typer`. `dataclasses` (stdlib 3.7+), `enum` (stdlib), and `csv` (stdlib) cover the data model and input reading. `tomllib` (stdlib 3.11+) already handles TOML parsing in Phase 1 — Phase 2 adds field-presence validation on top of the returned dict. The `typer` library (already in `pyproject.toml`) handles the `--input` CLI argument with automatic `--help` generation and type coercion.

The biggest design decision is the status field type. Using a string `Literal` type or an `Enum` with a fixed set of values prevents silent typos in later phases (e.g., writing `"sent"` vs `"Sent"`). Using a `dataclass` rather than a `TypedDict` or plain dict gives field-level defaults and makes the class easily testable via direct instantiation.

**Primary recommendation:** Add `models.py` with a `CompanyRecord` dataclass and `Status` string enum. Extend `config.py` to validate required profile fields after loading. Update `__main__.py` to accept `--input <csv>` as a `typer.Option`, call `check_env()` and `load_profile()`, then exit cleanly.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| dataclasses | stdlib (3.7+) | `CompanyRecord` row model with typed fields and defaults | Zero dependency; `@dataclass` gives `__init__`, `__repr__`, `__eq__` for free; easy to serialize to dict for CSV writing |
| enum | stdlib | `Status` values as a typed string enum | Prevents typo bugs across phases; all valid status strings live in one place; compatible with `csv` writer (`.value`) |
| csv | stdlib | Read single-column CSV of URLs | No extra dependency; handles quoting and encoding edge cases correctly; `csv.DictReader` or `csv.reader` both work |
| typer | >=0.24.1 (already in pyproject.toml) | `--input <csv>` CLI argument with `--help` | Already declared; `typer.Option` with `Path` type gives automatic existence validation and help text |
| tomllib | stdlib (3.11+) | TOML parsing (already used in config.py) | Already in use; Phase 2 adds validation logic on top of the returned dict |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib.Path | stdlib | Typed path argument for `--input` | typer accepts `Path` natively; gives `.exists()`, `.suffix` checks for free |
| datetime | stdlib | `timestamp` field in `CompanyRecord` | `datetime.datetime` with `field(default_factory=...)` gives per-instance timestamps |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@dataclass` for CompanyRecord | `TypedDict` | TypedDict is dict-compatible but has no defaults, no methods, no `__eq__`; dataclass is better for a mutable row model |
| `@dataclass` for CompanyRecord | `pydantic.BaseModel` | Pydantic adds validation power but is an extra dep not yet in pyproject.toml; stdlib dataclass is sufficient for a flat row struct |
| `str` Literal for status | `enum.Enum` subclass | Both work; `enum.Enum` with string values is preferred — provides IDE autocomplete, prevents silent typos, serialises to `.value` for CSV output |
| manual dict validation in config.py | pydantic-settings | Overkill for 4 required top-level keys; manual `_validate_profile()` is < 15 lines and fully testable |

**Installation:**
```bash
# No new dependencies — everything needed is in stdlib or already in pyproject.toml
uv pip install -e ".[dev]"  # ensures editable install is current
```

---

## Architecture Patterns

### Recommended Project Structure After Phase 2
```
src/job_mailer/
├── __init__.py          # (exists, empty)
├── __main__.py          # Extended: --input <csv>, check_env(), load_profile(), sys.exit(0)
├── config.py            # Extended: validate_profile() checks required fields
└── models.py            # NEW: CompanyRecord dataclass + Status enum

tests/
├── conftest.py          # (exists) autouse fixture clears env keys
├── test_config.py       # (exists) Phase 1 tests — do not modify
├── test_models.py       # NEW: CompanyRecord instantiation and field tests
└── test_cli.py          # NEW: CLI --input argument and exit-clean tests
```

### Pattern 1: CompanyRecord Dataclass with Status Enum

**What:** A `@dataclass` with all log fields (matching LOG-02 requirement), optional fields defaulting to empty string or None, and a `Status` string enum for the status column.

**When to use:** Any time a pipeline stage creates or updates a company record. All phases use the same type — never a raw dict.

**Example:**
```python
# src/job_mailer/models.py
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime


class Status(str, enum.Enum):
    """All valid pipeline status values."""
    PENDING = "pending"
    SENT = "sent"
    NO_EMAIL_FOUND = "no_email_found"
    GENERATION_FAILED = "generation_failed"
    SEND_FAILED = "send_failed"
    SKIPPED = "skipped"


@dataclass
class CompanyRecord:
    url: str
    company_name: str = ""
    email_found: str = ""
    generated_message: str = ""
    status: Status = Status.PENDING
    resend_message_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
```

### Pattern 2: Profile Field Validation Without KeyError

**What:** After `tomllib.load()` returns a dict, walk the required key paths and produce a single `sys.exit()` message listing all missing fields — not a bare `KeyError` traceback.

**When to use:** In `load_profile()` or a dedicated `validate_profile()` called immediately after loading.

**Example:**
```python
# Extension to src/job_mailer/config.py

_REQUIRED_PROFILE_FIELDS = [
    ("developer", "name"),
    ("developer", "title"),
    ("developer", "contact", "email"),
    ("developer", "skills", "primary"),
    ("developer", "skills", "specialisation"),
]


def validate_profile(profile: dict) -> None:
    """Raise SystemExit with actionable message if required profile fields are missing."""
    missing = []
    for path in _REQUIRED_PROFILE_FIELDS:
        node = profile
        for key in path:
            if not isinstance(node, dict) or key not in node:
                missing.append(".".join(path))
                break
            node = node[key]
    if missing:
        fields_list = "\n  ".join(missing)
        sys.exit(
            f"Error: profile.toml is missing required fields:\n  {fields_list}\n"
            f"\nSee profile.example.toml for all required fields."
        )
```

### Pattern 3: Typer CLI with --input Argument

**What:** Replace the stub `main()` with a Typer command that accepts `--input` as a `Path` option, validates config, then exits. The function does NOT start the pipeline — that is a later phase concern.

**When to use:** Phase 2 only adds the argument and startup validation. No CSV processing logic belongs here.

**Example:**
```python
# src/job_mailer/__main__.py
from __future__ import annotations

import sys
from pathlib import Path

import typer

from job_mailer.config import check_env, load_profile, validate_profile

app = typer.Typer()


@app.command()
def main(
    input: Path = typer.Option(..., "--input", help="CSV file of company URLs"),
) -> None:
    """job-mailer: CSV of company URLs -> personalized cold emails."""
    check_env()
    profile = load_profile()
    validate_profile(profile)
    # Pipeline not yet implemented
    typer.echo(f"Config loaded. Input file: {input}")
```

### Anti-Patterns to Avoid

- **Using `dict` as the row model:** Every downstream phase would need to know the exact key names as strings. A dataclass makes the contract explicit and detectable by a linter.
- **Catching `KeyError` from profile dict access:** `profile["developer"]["name"]` raises `KeyError` with an opaque key name. Always go through `validate_profile()` before accessing nested keys.
- **Importing `models.py` in `config.py`:** `config.py` is loaded at import time. Circular imports are easy to create if `models.py` imports `config.py` for the `Status` default. Keep them independent — `models.py` has no imports from `job_mailer`.
- **Using `typer.Argument` instead of `typer.Option` for `--input`:** The requirement specifies `--input <csv>` (an option, not a positional argument). `typer.Option` requires the `--input` flag explicitly; `typer.Argument` is positional.
- **Validating CSV existence in Phase 2:** Phase 2 success criterion says "exits cleanly after loading and validating config." CSV reading is pipeline logic — save it for Phase 3.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Row data model | Plain `dict` with string keys | `@dataclass` CompanyRecord | Typos in key names are silent; dataclass fields are checked by the linter |
| CSV reading | `open()` + `str.split(",")` | `csv.reader` or `csv.DictReader` | stdlib csv handles quoted fields, commas inside values, different line endings |
| CLI argument parsing | `sys.argv` parsing | `typer.Option` | typer generates `--help`, type-checks the path, and produces user-friendly error on missing required option |
| Profile field validation | Nested `try/except KeyError` in every caller | Centralised `validate_profile()` in `config.py` | Catches all missing fields at once with a single human-readable message |

**Key insight:** The entire phase is glue code between already-chosen libraries. The only custom logic is `validate_profile()` (< 15 lines) and the `CompanyRecord` dataclass definition. Everything else is standard library usage.

---

## Common Pitfalls

### Pitfall 1: Status Field as a Plain String

**What goes wrong:** Later phases write `record.status = "Sent"` or `record.status = "no_email"` (typo). The CSV log accepts it silently. `LOG-03` (skip rows where `status == "sent"`) then fails to skip them because the string doesn't match.

**Why it happens:** If `status` is typed as `str`, no validation runs at assignment time.

**How to avoid:** Type `status` as `Status` (the enum). Assign only `Status.SENT`, `Status.NO_EMAIL_FOUND`, etc. The enum `.value` is used when writing to CSV.

**Warning signs:** `record.status` contains a string that isn't one of the six enum values; LOG-03 idempotency check silently fails.

### Pitfall 2: validate_profile() Called After Profile Keys Are Accessed

**What goes wrong:** Some module imports from `config.py` and immediately accesses `profile["developer"]["name"]` before `validate_profile()` has been called. A missing key produces a raw `KeyError` with a cryptic message.

**Why it happens:** `load_profile()` returns a raw dict. Nothing stops callers from accessing keys directly.

**How to avoid:** In `__main__.py`, always call `validate_profile(profile)` immediately after `load_profile()` returns — before passing `profile` to any other function. Document this order in `config.py` module docstring.

**Warning signs:** `KeyError: 'name'` in a traceback instead of the clear `sys.exit()` message.

### Pitfall 3: Typer Path Option Does Not Validate File Existence by Default

**What goes wrong:** User passes `--input missing_file.csv`. Typer does not error — it creates a `Path` object for a non-existent file. The error only surfaces later when the file is opened.

**Why it happens:** `typer.Option` with `Path` type does type coercion but not existence validation unless explicitly configured.

**How to avoid:** Use `typer.Option(..., "--input", exists=True, readable=True, file_okay=True, dir_okay=False)` to get Typer to validate the path before `main()` runs.

**Warning signs:** `--input nonexistent.csv` runs without error until file open.

### Pitfall 4: dataclass `timestamp` Field Shared Across Instances

**What goes wrong:** Using `timestamp: str = datetime.utcnow().isoformat()` as a class-level default causes all instances to share the same timestamp string — the time when the module was first imported.

**Why it happens:** Mutable default expressions at class level in dataclasses are evaluated once at class definition, not per instance. Python raises a `ValueError` for mutable defaults like lists, but not for strings — so the timestamp bug is silent.

**How to avoid:** Use `field(default_factory=lambda: datetime.utcnow().isoformat())` so the timestamp is computed fresh for each instance.

**Warning signs:** All `CompanyRecord` instances have the same `timestamp` value regardless of when they were created.

---

## Code Examples

Verified patterns from official sources:

### CompanyRecord Dataclass (Full)
```python
# src/job_mailer/models.py
# Source: Python docs — dataclasses (https://docs.python.org/3/library/dataclasses.html)
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime


class Status(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    NO_EMAIL_FOUND = "no_email_found"
    GENERATION_FAILED = "generation_failed"
    SEND_FAILED = "send_failed"
    SKIPPED = "skipped"


@dataclass
class CompanyRecord:
    url: str
    company_name: str = ""
    email_found: str = ""
    generated_message: str = ""
    status: Status = Status.PENDING
    resend_message_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_csv_row(self) -> dict[str, str]:
        """Return a flat dict suitable for csv.DictWriter."""
        return {
            "url": self.url,
            "company_name": self.company_name,
            "email_found": self.email_found,
            "generated_message": self.generated_message,
            "status": self.status.value,
            "resend_message_id": self.resend_message_id,
            "timestamp": self.timestamp,
        }
```

### Profile Validation (Full)
```python
# Extension to src/job_mailer/config.py
# Source: Python docs — tomllib (https://docs.python.org/3/library/tomllib.html)

_REQUIRED_PROFILE_FIELDS: list[tuple[str, ...]] = [
    ("developer", "name"),
    ("developer", "title"),
    ("developer", "contact", "email"),
    ("developer", "skills", "primary"),
    ("developer", "skills", "specialisation"),
]


def validate_profile(profile: dict) -> None:
    """Raise SystemExit if any required profile.toml fields are absent."""
    missing = []
    for path in _REQUIRED_PROFILE_FIELDS:
        node = profile
        for key in path:
            if not isinstance(node, dict) or key not in node:
                missing.append(".".join(path))
                break
            node = node[key]
    if missing:
        fields_list = "\n  ".join(missing)
        sys.exit(
            f"Error: profile.toml is missing required fields:\n  {fields_list}\n"
            f"\nSee profile.example.toml for all required fields."
        )
```

### Typer --input Option with Path Validation
```python
# Source: Typer docs (https://typer.tiangolo.com/tutorial/options/)
import typer
from pathlib import Path

@app.command()
def main(
    input: Path = typer.Option(
        ...,
        "--input",
        help="Single-column CSV file of company URLs",
        exists=True,
        readable=True,
        file_okay=True,
        dir_okay=False,
    ),
) -> None:
    ...
```

### CSV Single-Column Reading
```python
# Source: Python docs — csv (https://docs.python.org/3/library/csv.html)
import csv
from pathlib import Path

def read_urls(csv_path: Path) -> list[str]:
    """Read company URLs from a single-column CSV. Skips header row if present."""
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = [row[0].strip() for row in reader if row and row[0].strip()]
    return rows
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `NamedTuple` for row models | `@dataclass` | Python 3.7 (2018) | Dataclass fields are mutable (needed for pipeline updates); NamedTuple is immutable |
| `argparse` for CLI | `typer` | typer 0.3+ (2021) | Typer is already in pyproject.toml; argparse would require parallel setup |
| `str` enum values | `class Status(str, enum.Enum)` | Python 3.11+ | `str` mixin means `Status.SENT == "sent"` is True — transparent in comparisons and CSV output |

**Deprecated/outdated:**
- `attrs` library: Superseded by stdlib `dataclasses` for this use case. Do not add as a dependency.
- `click` directly: Typer wraps click and is already chosen. Do not use click API directly.

---

## Open Questions

1. **`send.delay_seconds` validation range**
   - What we know: `profile.example.toml` documents `delay_seconds = 2` with a comment "minimum 1"
   - What's unclear: Whether `validate_profile()` should enforce the minimum-1 constraint or leave that to Phase 5
   - Recommendation: Phase 2 validates field *presence* only. Range validation (min 1) belongs in Phase 5 where the value is actually used.

2. **`timestamp` timezone: UTC vs local**
   - What we know: LOG-02 says "timestamp" with no timezone spec; `datetime.utcnow()` is deprecated in Python 3.12 in favour of `datetime.now(timezone.utc)`
   - What's unclear: Target Python minor version — `requires-python = ">=3.11"` allows both 3.11 and 3.12
   - Recommendation: Use `datetime.now(datetime.timezone.utc).isoformat()` — forwards-compatible with 3.12 and unambiguous for log consumers.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (latest, already installed) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — exists with `testpaths = ["tests"]` and `addopts = "-x"` |
| Quick run command | `pytest tests/test_models.py tests/test_cli.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INPUT-01 | `CompanyRecord` can be instantiated with only `url`; other fields have defaults | unit | `pytest tests/test_models.py::test_company_record_defaults -x` | Wave 0 |
| INPUT-01 | `CompanyRecord` has all 7 required fields: url, company_name, email_found, generated_message, status, resend_message_id, timestamp | unit | `pytest tests/test_models.py::test_company_record_fields -x` | Wave 0 |
| INPUT-01 | `Status` enum has all required values: pending, sent, no_email_found, generation_failed, send_failed, skipped | unit | `pytest tests/test_models.py::test_status_enum_values -x` | Wave 0 |
| INPUT-01 | `validate_profile()` raises `SystemExit` with field name when required field is missing | unit | `pytest tests/test_config.py::test_validate_profile_missing_field -x` | Wave 0 |
| INPUT-01 | `validate_profile()` passes silently when all required fields are present | unit | `pytest tests/test_config.py::test_validate_profile_all_present -x` | Wave 0 |
| INPUT-01 | CLI `--input file.csv` exits cleanly (exit code 0) after config loads | integration | `pytest tests/test_cli.py::test_cli_input_exits_clean -x` | Wave 0 |
| INPUT-01 | CLI without `--input` exits with non-zero code and usage message | unit | `pytest tests/test_cli.py::test_cli_missing_input_flag -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_models.py -x` (after models.py) or `pytest tests/test_config.py -x` (after config.py) or `pytest tests/test_cli.py -x` (after __main__.py)
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_models.py` — covers CompanyRecord and Status enum (REQ INPUT-01)
- [ ] `tests/test_cli.py` — covers `--input` argument and exit-clean behavior (REQ INPUT-01)
- [ ] `src/job_mailer/models.py` — does not yet exist; must be created in Wave 1

*(Existing `tests/test_config.py` and `tests/conftest.py` from Phase 1 are extended, not replaced.)*

---

## Sources

### Primary (HIGH confidence)
- [Python docs — dataclasses](https://docs.python.org/3/library/dataclasses.html) — `@dataclass`, `field(default_factory=...)`, `__init__` generation
- [Python docs — enum](https://docs.python.org/3/library/enum.html) — `str` mixin enum pattern; `.value` for serialization
- [Python docs — csv](https://docs.python.org/3/library/csv.html) — `csv.reader`, `csv.DictReader`, `DictWriter`, quoting behavior
- [Python docs — tomllib](https://docs.python.org/3/library/tomllib.html) — already confirmed in Phase 1 research
- [Typer docs — Options](https://typer.tiangolo.com/tutorial/options/) — `typer.Option`, `Path` type with `exists=True`
- Existing codebase — `src/job_mailer/config.py`, `src/job_mailer/__main__.py`, `tests/test_config.py`, `tests/conftest.py`, `profile.example.toml`, `pyproject.toml` — all read directly

### Secondary (MEDIUM confidence)
- [Python docs — datetime.now(tz)](https://docs.python.org/3/library/datetime.html#datetime.datetime.now) — `datetime.now(timezone.utc)` preferred over deprecated `utcnow()` in Python 3.12+

### Tertiary (LOW confidence)
- None — all critical claims verified against official sources or existing codebase.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are stdlib or already declared in pyproject.toml; APIs verified against official docs
- Architecture: HIGH — patterns match existing Phase 1 conventions (sys.exit, centralised validation, conftest autouse fixture)
- Pitfalls: HIGH — sourced from direct inspection of existing code patterns and Python dataclass documentation
- Test map: HIGH — existing pytest infrastructure confirmed working; test commands match installed framework

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stdlib and typer APIs are stable; no fast-moving dependencies involved)
