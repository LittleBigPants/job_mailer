# Stack Research

**Domain:** Python CLI tool — web scraping, LLM API, transactional email
**Researched:** 2026-03-14
**Confidence:** HIGH (all core versions verified against PyPI/official docs)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Runtime | 3.11 ships `tomllib` as stdlib (no extra dep for TOML config); 3.11+ required by Groq SDK. 3.11 is the minimum sensible floor. |
| Typer | 0.24.1 | CLI framework | Built on Click, uses Python type hints to auto-generate `--help`, argument validation, and shell completion with near-zero boilerplate. `--dry-run` flag and `--delay` option map cleanly to typed function params. Requires Python >=3.10. |
| httpx | 0.28.1 | HTTP client | Sync + async API in one package; HTTP/1.1 and HTTP/2; cleaner than `requests` for new code. Groq's official Python SDK already uses httpx internally, so the dependency is shared not added. |
| beautifulsoup4 | 4.14.3 | HTML parsing | Industry standard for scraping HTML structures (footer, contact links). Used with `lxml` as the underlying parser for performance. Tolerates malformed HTML well — important for real-world homepages. |
| lxml | 6.0.2 | HTML parser backend | C-based parser used by BeautifulSoup. Dramatically faster than the default `html.parser`. Install alongside bs4: `soup = BeautifulSoup(html, "lxml")`. |
| groq | 1.1.1 | Groq LLM API client | Official Groq Python SDK. OpenAI-compatible interface. `client.chat.completions.create(...)` is the call pattern. Sync and async. Python >=3.10. |
| resend | 2.23.0 | Email delivery | Official Resend Python SDK. Single-call API: `resend.Emails.send({...})`. No SMTP configuration. Python >=3.7. |
| tomllib (stdlib) | built-in ≥3.11 | TOML config parsing | Ships in Python 3.11+ standard library. Zero extra dependency for reading `profile.toml`. Read-only (sufficient — we never write config at runtime). |
| tenacity | 9.1.4 | Retry logic | Decorator-based retry with exponential backoff. Wrap httpx scrape calls and Groq/Resend API calls to handle transient failures cleanly. Python >=3.10. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | 1.x | `.env` file loading | Load `GROQ_API_KEY` and `RESEND_API_KEY` from a `.env` file at startup. Keeps secrets out of `profile.toml` and out of git. |
| csv (stdlib) | built-in | CSV read/write | Read input URL list; write output log. No external dep needed — stdlib `csv.DictReader` / `csv.DictWriter` handle both tasks for this volume of data. |
| logging (stdlib) | built-in | Run log output | Structured console output during execution. Configure a `FileHandler` to persist the human-readable run log. No third-party logger needed at this scale. |
| time (stdlib) | built-in | Send delay | `time.sleep(delay)` between sends. No extra dep — configurable via CLI option. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Package manager + virtual env | Fastest Python package installer (Rust-based). `uv venv && uv pip install -r requirements.txt`. Replaces pip + venv for local dev. |
| ruff | Linting + formatting | Single tool replacing flake8 + black + isort. `ruff check . && ruff format .`. Configured in `pyproject.toml`. |
| pytest | Testing | Standard Python test runner. `pytest tests/` covers unit tests for scraper logic, domain inference, CSV parsing. |
| python-dotenv | Dev secret loading | `.env` file for local API keys during development and testing. |

## Installation

```bash
# Create and activate virtual env
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Core runtime dependencies
uv pip install typer httpx beautifulsoup4 lxml groq resend tenacity python-dotenv

# Dev dependencies
uv pip install ruff pytest
```

Or with a `requirements.txt` / `pyproject.toml`:

```toml
# pyproject.toml [project.dependencies]
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
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Typer | Click | When you need fine-grained decorator control or have existing Click codebase; Typer wraps Click, so you can mix them |
| Typer | argparse (stdlib) | Only when zero dependencies is a hard constraint — argparse is verbose and has no auto-completion |
| httpx | requests | When targeting Python <3.8 or the team has a strong `requests` muscle memory; otherwise httpx is strictly better |
| beautifulsoup4 + lxml | selectolax | selectolax is faster for very high-volume scraping (1M+ pages); overkill for a personal job-search tool doing dozens of pages per run |
| beautifulsoup4 + lxml | playwright | Playwright handles JS-rendered pages; the PROJECT.md explicitly scopes out JS-heavy scraping — use playwright only if a target site requires it |
| tomllib (stdlib) | tomli (pip) | Use `tomli` only if the project must support Python 3.10 (where `tomllib` isn't stdlib); otherwise stdlib is always preferable |
| tomllib (stdlib) | tomlkit | Use tomlkit only if you need to *write* TOML back to disk (preserving comments/style); this project only reads config |
| stdlib logging | structlog | Use structlog for services emitting JSON logs to aggregators (Datadog, ELK); overkill for a personal CLI tool logging to a CSV and console |
| stdlib csv | pandas | Use pandas when doing analysis, aggregation, or working with large datasets; for simple row read/write, stdlib csv has zero overhead |
| tenacity | manual retry loop | Manual loops are fine for one-off retries; tenacity pays off once you have 3+ API call sites needing consistent exponential backoff |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `requests` | Synchronous-only, no HTTP/2, no async, older API style; httpx is a drop-in upgrade | `httpx` |
| `smtplib` (stdlib) | SMTP setup requires mail server config, SPF/DKIM alignment; deliverability is a non-trivial problem | `resend` SDK |
| `openai` SDK (for Groq) | Although Groq exposes an OpenAI-compatible API, using the openai SDK to call Groq adds an unnecessary indirect dependency and is fragile to OpenAI SDK major version changes | `groq` SDK |
| `pandas` for CSV I/O | Heavy dependency (~30MB) for reading a single-column URL list and writing a log file; stdlib `csv` does this in zero bytes | stdlib `csv` |
| `playwright` / `selenium` | JavaScript-heavy browser automation; the scraping scope (footer/contact/about text) does not require JS execution | `httpx` + `beautifulsoup4` |
| `argparse` | Verbose, no type inference, no auto-completion, no modern DX | `typer` |
| `toml` (pip) | Unmaintained third-party package; superseded by stdlib `tomllib` in Python 3.11+ | `tomllib` (stdlib) |
| `.env` for profile config | API keys belong in `.env`; developer profile (name, stack, links) is not a secret and belongs in a committed `profile.toml` for portability | `profile.toml` read with `tomllib` |

## Stack Patterns by Variant

**If a target company's contact page requires JavaScript to render:**
- Add `playwright` as an optional fallback for that specific URL
- Use `httpx` first; only invoke playwright if the initial parse finds no email
- Keep playwright out of the hot path (it's slow and heavyweight)

**If the user wants to run on Python 3.10 (before 3.11):**
- Add `tomli` as a dependency
- Use: `try: import tomllib except ImportError: import tomli as tomllib`
- All other packages support 3.10 already

**If email volume grows beyond personal use:**
- Replace `time.sleep()` with proper async rate-limiting via `asyncio` + `asyncio.Semaphore`
- httpx async client + Groq async client already support this pattern without library changes

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| groq 1.1.1 | Python >=3.10 | Uses httpx internally; no conflict with direct httpx dependency |
| typer 0.24.1 | Python >=3.10 | Sets the Python floor for the project |
| tenacity 9.1.4 | Python >=3.10 | Aligns with groq and typer floor |
| httpx 0.28.1 | Python >=3.8 | Backward compatible; no conflict |
| beautifulsoup4 4.14.3 | Python >=3.7 | No conflict |
| lxml 6.0.2 | Python >=3.8 | Binary wheels available for all major platforms |
| resend 2.23.0 | Python >=3.7 | No conflict |
| tomllib | Python >=3.11 (stdlib) | Use `tomli` pip package as shim for 3.10 |

## Sources

- [typer · PyPI](https://pypi.org/project/typer/) — version 0.24.1 confirmed, Python >=3.10 (HIGH confidence)
- [httpx · PyPI](https://pypi.org/project/httpx/) — version 0.28.1 confirmed, Python >=3.8 (HIGH confidence)
- [beautifulsoup4 · PyPI](https://pypi.org/project/beautifulsoup4/) — version 4.14.3 confirmed (HIGH confidence)
- [lxml · PyPI](https://pypi.org/project/lxml/) — version 6.0.2 confirmed (HIGH confidence)
- [groq · PyPI](https://pypi.org/project/groq/) — version 1.1.1 confirmed, Python >=3.10 (HIGH confidence)
- [resend · PyPI](https://pypi.org/project/resend/) — version 2.23.0 confirmed, Python >=3.7 (HIGH confidence)
- [tenacity · PyPI](https://pypi.org/project/tenacity/) — version 9.1.4 confirmed (HIGH confidence)
- [tomllib — Python 3.14.3 docs](https://docs.python.org/3/library/tomllib.html) — stdlib since 3.11, read-only (HIGH confidence)
- [Typer official site](https://typer.tiangolo.com/) — Click vs Typer comparison, type hints approach (HIGH confidence)
- [httpx official site](https://www.python-httpx.org/) — HTTP/2, sync+async API (HIGH confidence)
- WebSearch: "python httpx BeautifulSoup web scraping stack 2025" — httpx+bs4 combination confirmed as current standard (MEDIUM confidence, corroborates official docs)
- WebSearch: "python lxml vs beautifulsoup4 html parsing 2025" — lxml as bs4 backend recommended for performance (MEDIUM confidence)
- WebSearch: "python tomllib stdlib 3.11 toml config file parsing 2025" — tomllib read-only limitation confirmed (HIGH confidence, multiple sources)
- WebSearch: "python CSV stdlib csv module vs pandas 2025 simple tool" — stdlib csv recommended for simple tooling (MEDIUM confidence)

---
*Stack research for: Python CLI cold email outreach tool*
*Researched: 2026-03-14*
