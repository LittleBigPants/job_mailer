# Phase 1: Scaffolding - Research

**Researched:** 2026-03-14
**Domain:** Python project scaffolding — secrets management, TOML schema, DNS authentication documentation
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | Project includes README documentation for required DNS auth setup (SPF/DKIM/DMARC) before any live sends | Resend DNS record formats verified; record structure documented in Code Examples section |
| INFRA-02 | API keys loaded from .env via python-dotenv; .env is gitignored from project setup | python-dotenv 1.2.2 API verified; startup validation pattern documented; .gitignore conventions documented |
| INFRA-03 | profile.toml has a locked schema with a profile.example.toml committed to the repo | tomllib stdlib (Python 3.11+) confirmed; TOML schema structure and example file conventions documented |
</phase_requirements>

---

## Summary

Phase 1 establishes the foundation that makes all subsequent phases safe to build. Three things must be true before any code that touches external APIs or sends real email is written: API keys cannot be accidentally committed, the developer profile schema is locked so later phases can rely on it without renegotiating field names, and DNS authentication is documented so the tool is usable by anyone who clones the repo.

The technical surface area is narrow — `python-dotenv` for secret loading, `tomllib` (stdlib) for profile parsing, a `.gitignore` entry, and a `pyproject.toml` for project packaging. The main complexity is not code but discipline: establishing the right file separation (`profile.toml` for commit-safe profile data, `.env` for secrets) and producing documentation that is actionable before a developer touches the Resend dashboard.

The scaffolding phase also establishes the `pyproject.toml` that anchors dependency management for all future phases, making it load-bearing infrastructure rather than a throwaway config file.

**Primary recommendation:** Create `pyproject.toml` + `src/job_mailer/` package layout, add `.env` to `.gitignore` on first commit before the file exists, implement a `_check_env()` startup function using `python-dotenv` + `os.environ`, commit `profile.example.toml` with typed comments, and add a DNS section to `README.md` covering Resend-specific SPF/DKIM/DMARC record formats.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-dotenv | 1.2.2 | Load `.env` into `os.environ` at startup | Zero-config; `load_dotenv()` is one call; reads `.env` transparently; does not override real env vars |
| tomllib | stdlib (Python 3.11+) | Parse `profile.toml` at startup | No extra dependency; ships in Python 3.11+ stdlib; read-only, which is all this project needs |
| uv | latest | Virtual env + dependency installation | Project already selected uv (see STACK.md); `uv init` scaffolds `pyproject.toml` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | latest | Test runner | Needed even in Phase 1 for the `_check_env()` validation function tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| plain `os.environ.get()` for validation | pydantic-settings | pydantic-settings is excellent but adds a dependency; for 3 keys, a manual `_check_env()` with `os.environ` is zero-overhead and fully testable |
| tomllib (stdlib) | tomli (pip) | Use `tomli` only if Python 3.10 support is needed; project targets 3.11+, so stdlib wins |

**Installation:**
```bash
# uv init creates pyproject.toml; then add runtime deps for this phase:
uv pip install python-dotenv pytest
```

---

## Architecture Patterns

### Recommended Project Structure

This phase creates the skeleton. Later phases fill it in.

```
job_mailer/                      # repo root
├── .env                         # never committed — secrets only
├── .env.example                 # committed — documents required keys, no real values
├── .gitignore                   # committed — .env must appear here on first commit
├── LICENSE
├── README.md                    # committed — includes DNS setup section
├── pyproject.toml               # committed — project metadata + dependencies
├── profile.example.toml         # committed — schema reference with all fields + types
├── profile.toml                 # never committed — developer's real profile values
├── src/
│   └── job_mailer/
│       ├── __init__.py
│       └── config.py            # load_dotenv() call + _check_env() validation
└── tests/
    └── test_config.py           # tests for _check_env() behavior
```

### Pattern 1: Startup Environment Validation

**What:** Call `load_dotenv()` once at module import time in `config.py`, then immediately validate all required keys are present. Raise `SystemExit` with a human-readable message on failure, not a `KeyError` traceback.

**When to use:** Always — this is the entry point contract. Every other module imports from `config.py` so validation runs before any API call is attempted.

**Example:**
```python
# src/job_mailer/config.py
# Source: python-dotenv 1.2.2 docs (https://pypi.org/project/python-dotenv/)
import os
import sys
from dotenv import load_dotenv

load_dotenv()  # reads .env into os.environ; no-op if .env absent

_REQUIRED_ENV_KEYS = [
    "GROQ_API_KEY",
    "RESEND_API_KEY",
    "RESEND_FROM_EMAIL",
]


def check_env() -> None:
    """Validate required environment variables are present. Call once at startup."""
    missing = [k for k in _REQUIRED_ENV_KEYS if not os.environ.get(k)]
    if missing:
        missing_str = "\n  ".join(missing)
        sys.exit(
            f"Missing required environment variables:\n  {missing_str}\n"
            f"Copy .env.example to .env and fill in the values."
        )
```

### Pattern 2: Separate Committed Schema from Live Secrets

**What:** Two parallel files with different git treatment:
- `profile.example.toml` — committed, all fields present with placeholder values and inline comments
- `profile.toml` — gitignored, actual developer data
- `.env.example` — committed, all keys listed with empty or placeholder values
- `.env` — gitignored, actual secrets

**When to use:** Always for any personal tool mixing profile config with API credentials. Separation is enforced by `.gitignore`, not by convention alone.

**Example `.gitignore` entries (must exist before `profile.toml` or `.env` are created):**
```gitignore
# Secrets and personal profile — never commit
.env
profile.toml

# Runtime artifacts
*.log
__pycache__/
.venv/
*.pyc
```

### Pattern 3: TOML Schema with Typed Comments

**What:** `profile.example.toml` documents every field with its type and an example value in inline comments. `tomllib.load()` parsing code validates required fields are present at startup, parallel to `_check_env()`.

**When to use:** Lock the schema here in Phase 1 so Phase 4 (LLM generation) and Phase 5 (sending) can assume field names without renegotiating.

**Example:**
```toml
# profile.example.toml
# Copy this file to profile.toml and fill in your details.
# profile.toml is gitignored — never commit your real profile.

[developer]
name = "Jane Smith"                    # string — your full name for email signatures
title = "Senior Software Engineer"     # string — your current/target title
location = "Berlin, Germany"           # string — city, country
years_experience = 8                   # integer — years of professional experience

[developer.contact]
email = "jane@example.com"             # string — your reply-to email
github = "https://github.com/jsmith"  # string — GitHub profile URL
linkedin = ""                          # string — LinkedIn URL (optional, leave blank)
portfolio = ""                         # string — portfolio URL (optional)

[developer.skills]
primary = ["Python", "TypeScript", "Go"]  # list[string] — top 3-5 languages/frameworks
specialisation = "backend APIs and data pipelines"  # string — one-line summary

[send]
delay_seconds = 2   # integer — seconds between sends (minimum 1; default 2)
```

### Anti-Patterns to Avoid

- **Putting API key placeholders in `profile.example.toml`:** Even placeholder values normalise the anti-pattern. Keys belong exclusively in `.env.example`.
- **Writing `.gitignore` after creating `.env`:** Git may have already staged the file. Add `.env` to `.gitignore` on the very first commit, before the file exists.
- **Calling `load_dotenv()` inside a function:** Call it at module top-level so it runs on import. If called inside a function, it may be called after `os.environ` is already read elsewhere.
- **Using `os.environ["KEY"]` directly:** This raises `KeyError` with a raw traceback. Always go through `check_env()` first, then use `os.environ.get()` or `os.environ["KEY"]` only after validation has confirmed presence.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Loading `.env` file into environment | Custom file parser with `open()` + `split("=")` | `python-dotenv` `load_dotenv()` | Handles quoted values, multiline strings, comments, unicode, and `export KEY=val` format without extra code |
| TOML file parsing | Custom parser or `configparser` | `tomllib.load()` (stdlib 3.11+) | Handles nested tables, arrays, inline tables, date types, multiline strings — all format edge cases |
| Missing env var validation | `try/except KeyError` scattered across modules | Centralised `check_env()` called once at startup | Catches all missing keys at once, produces actionable message, tested in isolation |

**Key insight:** The only custom code needed here is the `check_env()` function and the `profile.toml` loader. Everything else is one-liner standard library or `python-dotenv` usage.

---

## Common Pitfalls

### Pitfall 1: `.env` Committed Before `.gitignore` Exists

**What goes wrong:** Developer creates `.env` first, runs `git add .`, keys are staged. Even after adding `.gitignore`, the file is tracked.
**Why it happens:** The natural instinct is to create the file you need, then worry about ignoring it later.
**How to avoid:** Create `.gitignore` with `.env` and `profile.toml` entries as the very first commit — before either file exists.
**Warning signs:** `git status` shows `.env` as a tracked or modified file.

### Pitfall 2: `profile.toml` Schema Drifts Between Example and Real Usage

**What goes wrong:** `profile.example.toml` is written once and never updated. Later phases add fields to the schema. The example becomes out of date and new contributors miss required fields.
**Why it happens:** Phase 1 creates the example file. Phase 4 adds `[send]` options without updating the example.
**How to avoid:** Treat `profile.example.toml` as the authoritative schema contract. Any new field added to the TOML loader must be added to the example file in the same commit.
**Warning signs:** `profile.example.toml` is missing fields that `config.py` expects.

### Pitfall 3: `load_dotenv()` Called Too Late

**What goes wrong:** Another module reads `os.environ.get("GROQ_API_KEY")` before `config.py` has been imported. The key is missing even though `.env` has it.
**Why it happens:** Python's import order is not always obvious. If `config.py` is imported lazily or `load_dotenv()` is inside a function, it may not run until after env vars are first accessed.
**How to avoid:** Put `load_dotenv()` at module top-level in `config.py`. Ensure `config.py` is the first import in `__main__.py` or the Typer entry point.
**Warning signs:** Keys intermittently missing in tests even though `.env` is present.

### Pitfall 4: DNS Section in README Is Too Vague to Follow

**What goes wrong:** README says "set up SPF, DKIM, and DMARC" with no record values or DNS provider steps. The developer skips it and sends from an unauthenticated domain. Emails land in spam or damage sender reputation.
**Why it happens:** Developers treat DNS docs as obvious ("everyone knows how to do DNS"). It's not obvious for someone new to transactional email.
**How to avoid:** The DNS section must include exact record types, names, and value formats for Resend specifically. It should include a verification step (MXToolbox or similar) before any live send is attempted.
**Warning signs:** README DNS section is < 10 lines or contains no DNS record examples.

---

## Code Examples

### `config.py` — Full Startup Module
```python
# Source: python-dotenv 1.2.2 (https://pypi.org/project/python-dotenv/)
# src/job_mailer/config.py
from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # loads .env relative to cwd; no-op if absent

_REQUIRED_ENV_KEYS = ["GROQ_API_KEY", "RESEND_API_KEY", "RESEND_FROM_EMAIL"]
_PROFILE_PATH = Path("profile.toml")


def check_env() -> None:
    """Raise SystemExit with actionable message if required env vars are missing."""
    missing = [k for k in _REQUIRED_ENV_KEYS if not os.environ.get(k)]
    if missing:
        keys_list = "\n  ".join(missing)
        sys.exit(
            f"Error: missing required environment variable(s):\n  {keys_list}\n"
            f"\nCopy .env.example to .env and fill in the values."
        )


def load_profile(path: Path = _PROFILE_PATH) -> dict:
    """Load and return developer profile from TOML file."""
    if not path.exists():
        sys.exit(
            f"Error: profile file not found at '{path}'.\n"
            f"Copy profile.example.toml to profile.toml and fill in your details."
        )
    with open(path, "rb") as f:
        return tomllib.load(f)
```

### `.env.example`
```bash
# .env.example — committed to repo
# Copy this file to .env and fill in real values.
# .env is gitignored and must NEVER be committed.

GROQ_API_KEY=gsk_your_groq_api_key_here
RESEND_API_KEY=re_your_resend_api_key_here
RESEND_FROM_EMAIL=outreach@yourdomain.com
```

### `pyproject.toml` — Minimal Project Scaffold
```toml
# Source: Python Packaging User Guide (https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
[project]
name = "job-mailer"
version = "0.1.0"
description = "CLI tool: CSV of company URLs -> personalized cold emails via Groq + Resend"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.24.1",
    "httpx>=0.28.1",
    "beautifulsoup4>=4.14.3",
    "lxml>=6.0.2",
    "groq>=1.1.1",
    "resend>=2.23.0",
    "tenacity>=9.1.4",
    "python-dotenv>=1.0",
]

[project.scripts]
job-mailer = "job_mailer.__main__:app"

[project.optional-dependencies]
dev = ["pytest", "ruff"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py311"
```

### README DNS Section Template
```markdown
## DNS Setup (Required Before First Live Send)

Before sending any emails, authenticate your sender domain with Resend.
Use a **dedicated subdomain** (e.g., `outreach.yourdomain.com`) — never your primary domain.
Cold email volume can damage sender reputation; keep it isolated.

### Step 1: Add your domain in Resend

1. Go to [Resend Dashboard > Domains](https://resend.com/domains)
2. Click "Add Domain"
3. Enter your sending subdomain (e.g., `outreach.yourdomain.com`)
4. Resend will show you two required DNS records

### Step 2: Add DNS records at your DNS provider

Add the following records (Resend will give you exact values for DKIM):

| Type | Name | Value |
|------|------|-------|
| TXT  | `send` | `v=spf1 include:amazonses.com ~all` |
| TXT  | `resend._domainkey` | *(copy from Resend dashboard — unique per domain)* |
| MX   | `send` | `feedback-smtp.us-east-1.amazonses.com` (priority 10) |

### Step 3: Add DMARC (recommended)

Add a DMARC record to build additional trust with mailbox providers:

| Type | Name | Value |
|------|------|-------|
| TXT  | `_dmarc` | `v=DMARC1; p=none; rua=mailto:dmarc@yourdomain.com` |

Start with `p=none` to monitor without rejecting. Move to `p=quarantine` after reviewing reports.

### Step 4: Verify

Check your records are live:
- [MXToolbox SPF Lookup](https://mxtoolbox.com/spf.aspx)
- [MXToolbox DKIM Lookup](https://mxtoolbox.com/dkim.aspx)
- [MXToolbox DMARC Lookup](https://mxtoolbox.com/dmarc.aspx)

Do not run a live send until Resend shows "Verified" for your domain in the dashboard.
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `python-dotenv` read from `.env` in project root | `python-dotenv` 1.2.2 unchanged pattern — `load_dotenv()` at module top | Stable API, no breaking changes | No migration needed |
| `import toml` (unmaintained pip package) | `import tomllib` (Python 3.11+ stdlib) | Python 3.11 (Oct 2022) | Zero extra dependency |
| `requirements.txt` | `pyproject.toml` with `[project.dependencies]` | PEP 621, now standard | uv, pip, and all modern tools read pyproject.toml natively |

**Deprecated/outdated:**
- `toml` (pip): Unmaintained; replaced by stdlib `tomllib` for 3.11+. Do not use.
- `configparser` / `.ini` files: Still works but TOML is now the Python-ecosystem standard for config files.

---

## Open Questions

1. **`profile.toml` exact field set for Phase 4 (LLM generation)**
   - What we know: Phase 4 uses `developer.name`, `developer.skills.primary`, `developer.specialisation`
   - What's unclear: Exact fields the Groq prompt template will reference — Phase 4 hasn't been planned yet
   - Recommendation: Lock the fields documented in `profile.example.toml` as the authoritative contract. Phase 4 must declare any additions in the same commit that modifies `config.py`.

2. **Whether `RESEND_FROM_EMAIL` is an env var or a profile field**
   - What we know: REQUIREMENTS.md lists it as an env var alongside API keys
   - What's unclear: Semantically, the "from" address is closer to profile config than a secret
   - Recommendation: Follow the requirements spec — load from `.env`. This avoids scope creep in Phase 1 and the requirements are explicit.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (latest) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — Wave 0 gap |
| Quick run command | `pytest tests/test_config.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-02 | `check_env()` raises `SystemExit` with message when a key is missing | unit | `pytest tests/test_config.py::test_check_env_missing_key -x` | Wave 0 |
| INFRA-02 | `check_env()` passes silently when all 3 keys present | unit | `pytest tests/test_config.py::test_check_env_all_present -x` | Wave 0 |
| INFRA-02 | `check_env()` error message names the missing key, not a traceback | unit | `pytest tests/test_config.py::test_check_env_names_missing_key -x` | Wave 0 |
| INFRA-02 | `.env` is absent from git tracking | smoke | `git status --short \| grep -v "^?" \| grep "\.env"` returns empty | N/A — manual |
| INFRA-03 | `load_profile()` returns dict with expected top-level keys | unit | `pytest tests/test_config.py::test_load_profile_schema -x` | Wave 0 |
| INFRA-03 | `load_profile()` raises `SystemExit` with message when `profile.toml` missing | unit | `pytest tests/test_config.py::test_load_profile_missing_file -x` | Wave 0 |
| INFRA-01 | README contains DNS section with SPF, DKIM, DMARC | smoke | `grep -c "SPF\|DKIM\|DMARC" README.md` returns >= 3 | N/A — manual check |

### Sampling Rate
- **Per task commit:** `pytest tests/test_config.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/__init__.py` — makes tests a package
- [ ] `tests/test_config.py` — covers INFRA-02 and INFRA-03 unit tests (5 test functions)
- [ ] `pyproject.toml` `[tool.pytest.ini_options]` block — test discovery config
- [ ] Framework install: `uv pip install pytest` — if not yet installed

---

## Sources

### Primary (HIGH confidence)
- [python-dotenv · PyPI](https://pypi.org/project/python-dotenv/) — version 1.2.2 confirmed (released 2026-03-01), `load_dotenv()` API verified
- [tomllib — Python 3.11 stdlib docs](https://docs.python.org/3/library/tomllib.html) — read-only, `tomllib.load(fp)` requires binary mode `"rb"` (HIGH — from STACK.md which cites official docs)
- [Resend Domains documentation](https://resend.com/docs/dashboard/domains/introduction) — SPF/DKIM record format verified; DMARC optional but recommended
- [Resend Cloudflare DNS guide](https://resend.com/docs/dashboard/domains/cloudflare) — exact DNS record types and name formats confirmed (TXT `send`, TXT `resend._domainkey`, MX `send`)
- [Python Packaging User Guide — pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) — `[project.dependencies]` format verified

### Secondary (MEDIUM confidence)
- [uv projects guide](https://docs.astral.sh/uv/guides/projects/) — `uv init` scaffolds `pyproject.toml`; project structure patterns
- [DMARCLY — DMARC/DKIM/SPF implementation guide](https://dmarcly.com/blog/how-to-implement-dmarc-dkim-spf-to-stop-email-spoofing-phishing-the-definitive-guide) — DMARC `p=none` starter policy recommended; SPF+DKIM must exist before DMARC
- [Cloudflare — What are DMARC, DKIM, SPF](https://www.cloudflare.com/learning/email-security/dmarc-dkim-spf/) — DNS record format reference

### Tertiary (LOW confidence)
- None — all critical claims verified against official sources.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — python-dotenv 1.2.2 and tomllib stdlib confirmed against PyPI and official Python docs
- Architecture: HIGH — patterns are standard Python; no novel approaches used
- DNS record formats: HIGH — verified against Resend official docs
- Pitfalls: HIGH — sourced from PITFALLS.md (already researched) + direct verification

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (python-dotenv and pyproject.toml conventions are stable; Resend DNS record format may change if they migrate away from SES)
