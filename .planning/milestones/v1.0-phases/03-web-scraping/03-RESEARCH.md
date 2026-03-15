# Phase 3: Web Scraping - Research

**Researched:** 2026-03-14
**Domain:** HTTP scraping, HTML parsing, email extraction, Python
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Collect all email candidates from mailto: links and page text (regex), score by priority list
- Priority order (highest to lowest):
  1. Preferred: jobs@, hiring@, contact@, hello@, hi@, team@
  2. Deprioritized: info@, admin@, support@
  3. Never return: noreply@, no-reply@, mailer@, donotreply@
- If only never-return addresses found: treat as no_email_found
- If only deprioritized addresses found: return the first deprioritized one found
- Per-page timeout: 10 seconds
- No retries — log warning and skip page; treat as "no email on this page"
- Continue fallback chain even if one page errors (404 on /contact means try /about)
- All three pages fail: log status as `scrape_failed` (distinct from `no_email_found`)
- `scrape_failed` requires adding `Status.SCRAPE_FAILED` enum value to `models.py`
- Use realistic Chrome-like User-Agent header on all requests
- Follow HTTP redirects automatically
- No delay between page requests within a single company
- Company name derived from domain slug (e.g. `stripe.com` -> "Stripe")

### Claude's Discretion
- HTML parsing library choice (BeautifulSoup vs regex-only for link extraction)
- Exact User-Agent string to use
- Module structure (e.g. `scraper.py` module name and function signatures)
- How to build fallback page URLs from the base domain (URL joining logic)
- How to handle acronyms or compound names — simple title-case of slug is acceptable baseline

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DISC-01 | Scraper extracts contact email from homepage via mailto: link parsing and regex pattern matching on full page text | BeautifulSoup4 `find_all('a', href=re.compile(r'^mailto:'))` + `re.findall` on `soup.get_text()` |
| DISC-02 | If no email found on homepage, falls back to /contact page using same extraction logic | URL joining with `urllib.parse.urljoin(base_url, '/contact')` + reuse extraction function |
| DISC-03 | If no email found on /contact, falls back to /about page using same extraction logic | Same pattern; `urljoin(base_url, '/about')` |
| DISC-04 | If no email found after all three pages, logs status as 'no_email_found' and continues to next company without stopping the run | Return `CompanyRecord` with `status=Status.NO_EMAIL_FOUND`; scrape_failed if all pages errored |
</phase_requirements>

---

## Summary

Phase 3 implements a three-page HTTP scraper that discovers a contact email for each company URL. The pipeline is synchronous and sequential — one company at a time, up to three pages per company (homepage, /contact, /about). Email candidates are collected from both mailto: href attributes and plain text regex matches, then scored against a priority list to select the best candidate.

The project already has `httpx`, `beautifulsoup4`, and `lxml` as declared dependencies in `pyproject.toml`. The CONTEXT.md describes the HTTP client as "`requests`", but `httpx` is already installed and provides an equivalent synchronous interface. The planner MUST use `httpx` (not `requests`) — adding `requests` would be a duplicate dependency for no benefit. `httpx` synchronous usage is nearly identical to `requests` (`httpx.get()`, `httpx.Client()`, `response.text`, `response.status_code`).

BeautifulSoup4 with lxml backend is the right choice for link extraction (fast, robust HTML parsing). Regex on `soup.get_text()` handles emails that appear in plain text but not in mailto: hrefs.

**Primary recommendation:** Implement `scraper.py` with a single public function `scrape_company(url: str) -> CompanyRecord` that runs the three-page fallback chain, uses `httpx.Client` with a 10-second timeout and `follow_redirects=True`, parses with `BeautifulSoup(html, 'lxml')`, and applies the priority scoring logic to select the best email candidate.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | >=0.28.1 (already in pyproject.toml) | Synchronous HTTP requests with timeout and redirect control | Already a project dependency; equivalent to requests with async capability for future phases |
| beautifulsoup4 | >=4.14.3 (already in pyproject.toml) | HTML parsing, mailto: link extraction | Industry standard; handles malformed HTML gracefully |
| lxml | >=6.0.2 (already in pyproject.toml) | BS4 parser backend | Fastest BS4 parser; already a declared dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| re (stdlib) | stdlib | Email regex extraction from page text | Complement to BS4 link parsing; catches emails in plain text |
| urllib.parse.urljoin (stdlib) | stdlib | Build /contact and /about URLs from base URL | Handles edge cases (trailing slash, path prefix) correctly |
| pytest-httpx | 0.36.0 | Mock httpx responses in tests | Required for unit testing the scraper without network calls |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | requests | requests is NOT in pyproject.toml; httpx is already installed and provides identical sync API — use httpx |
| lxml backend | html.parser | lxml is faster and already installed; html.parser is pure Python fallback only |
| urllib.parse.urljoin | string concatenation | urljoin handles edge cases (existing paths, trailing slashes) — do not concatenate manually |

**Installation:**

No new packages needed. All runtime dependencies are already in `pyproject.toml`. Only the test dependency needs adding:

```bash
uv add --dev pytest-httpx
```

---

## Architecture Patterns

### Recommended Project Structure
```
src/job_mailer/
├── scraper.py          # new: scrape_company(), _extract_emails(), _score_email()
├── models.py           # existing: add Status.SCRAPE_FAILED
├── config.py           # existing: unchanged
└── __main__.py         # existing: add CSV reading + scraper loop

tests/
├── test_scraper.py     # new: scraper unit tests using pytest-httpx
├── conftest.py         # existing: add httpx_mock setup if needed
└── ...
```

### Pattern 1: Flat module — `scraper.py` with one public function

**What:** A single module with one public function and private helpers. Caller only interacts with `scrape_company(url)`.
**When to use:** Always — the scraper has one job and one public contract.

```python
# src/job_mailer/scraper.py
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from job_mailer.models import CompanyRecord, Status

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_TIMEOUT = 10.0

_PREFERRED   = {"jobs", "hiring", "contact", "hello", "hi", "team"}
_DEPRIORITIZED = {"info", "admin", "support"}
_NEVER_RETURN  = {"noreply", "no-reply", "mailer", "donotreply"}


def scrape_company(url: str) -> CompanyRecord:
    """Scrape up to three pages and return a populated CompanyRecord."""
    ...
```

### Pattern 2: httpx synchronous Client with timeout and redirect

**What:** Use `httpx.Client` as a context manager; set timeout and follow_redirects at construction time so every request within the scrape inherits them.
**When to use:** When making multiple requests per invocation (one client reuses connection pool).

```python
# Source: https://www.python-httpx.org/advanced/clients/
with httpx.Client(
    headers={"User-Agent": _USER_AGENT},
    timeout=_TIMEOUT,
    follow_redirects=True,
) as client:
    response = client.get(url)
```

### Pattern 3: URL construction with urljoin

**What:** Build fallback page URLs from the base domain using `urllib.parse.urljoin`.
**When to use:** Always — handles trailing slashes, existing paths, and scheme normalization.

```python
from urllib.parse import urljoin

# Normalize base to scheme + netloc only
from urllib.parse import urlparse
parsed = urlparse(url)
base = f"{parsed.scheme}://{parsed.netloc}"

contact_url = urljoin(base, "/contact")  # https://stripe.com/contact
about_url   = urljoin(base, "/about")    # https://stripe.com/about
```

### Pattern 4: Email extraction — dual-source, then score

**What:** Extract candidates from (1) `<a href="mailto:...">` tags and (2) regex on full page text; merge into a set; score each against the priority list; return best.
**When to use:** Always — mailto: links are authoritative but some sites put emails only in plain text.

```python
def _extract_emails(html: str) -> list[str]:
    """Return all unique email candidates from a page, normalized to lowercase."""
    soup = BeautifulSoup(html, "lxml")
    found: set[str] = set()

    # Source 1: mailto: href attributes
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.lower().startswith("mailto:"):
            email = href[7:].split("?")[0].strip().lower()
            if email:
                found.add(email)

    # Source 2: regex on visible text
    for match in _EMAIL_RE.findall(soup.get_text()):
        found.add(match.lower())

    return list(found)


def _score_email(email: str) -> int:
    """Return sort key: 0=preferred, 1=deprioritized, 2=never-return, 3=other."""
    local = email.split("@")[0].lower()
    if local in _NEVER_RETURN:
        return 2
    if local in _PREFERRED:
        return 0
    if local in _DEPRIORITIZED:
        return 1
    return 1  # unknown addresses treated as deprioritized


def _best_email(candidates: list[str]) -> str | None:
    """Select highest-priority email; return None if only never-return addresses."""
    if not candidates:
        return None
    ranked = sorted(candidates, key=_score_email)
    best = ranked[0]
    if _score_email(best) == 2:
        return None  # only never-return addresses found
    return best
```

### Pattern 5: Company name from domain slug

**What:** Strip `www.` prefix, take the first label of the domain, title-case it.
**When to use:** Always as the baseline; user accepted this as sufficient.

```python
from urllib.parse import urlparse

def _infer_company_name(url: str) -> str:
    host = urlparse(url).hostname or ""
    host = host.removeprefix("www.")
    slug = host.split(".")[0]
    return slug.title()  # "stripe" -> "Stripe"
```

### Pattern 6: Three-page fallback with scrape_failed detection

**What:** Attempt homepage, /contact, /about in order. Track whether ANY page succeeded (2xx). If all failed with network errors: `scrape_failed`. If pages loaded but no email found: `no_email_found`.

```python
FALLBACK_PATHS = ["", "/contact", "/about"]

def scrape_company(url: str) -> CompanyRecord:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    company_name = _infer_company_name(url)
    record = CompanyRecord(url=url, company_name=company_name)

    all_candidates: list[str] = []
    any_page_succeeded = False

    with httpx.Client(
        headers={"User-Agent": _USER_AGENT},
        timeout=_TIMEOUT,
        follow_redirects=True,
    ) as client:
        for path in FALLBACK_PATHS:
            page_url = urljoin(base, path) if path else url
            try:
                resp = client.get(page_url)
                if resp.status_code == 200:
                    any_page_succeeded = True
                    page_candidates = _extract_emails(resp.text)
                    all_candidates.extend(page_candidates)
                    best = _best_email(all_candidates)
                    if best:
                        record.email_found = best
                        record.status = Status.SENT  # will be overwritten later; caller sets final status
                        return record
                # non-200: treat as "no email on this page", try next
            except (httpx.TimeoutException, httpx.RequestError):
                # log warning here
                pass

    # All pages exhausted
    best = _best_email(all_candidates)
    if best:
        record.email_found = best
        return record  # status stays PENDING for caller

    if not any_page_succeeded:
        record.status = Status.SCRAPE_FAILED
    else:
        record.status = Status.NO_EMAIL_FOUND
    return record
```

### Anti-Patterns to Avoid

- **String URL concatenation:** `url + "/contact"` breaks when `url` has a trailing slash or existing path. Use `urljoin`.
- **Parsing raw HTML with regex alone:** Regex on `<a href=...>` tags misses attributes with different quote styles or whitespace. Use BeautifulSoup for tag extraction, regex for text-body only.
- **`requests` library:** NOT in pyproject.toml. Adding it duplicates functionality already provided by `httpx`.
- **Accumulating candidates per-page then discarding across pages:** The spec collects candidates across ALL pages visited so far before calling `_best_email`. Don't reset the candidate list between pages.
- **Returning early before checking all higher-priority pages:** The three-page fallback exists because later pages might have better emails. The implementation above returns early if a preferred email is found, which is correct — but must not return early on a deprioritized email if a higher-priority page hasn't been checked yet. Simpler and more correct: accumulate all candidates across all pages and score at the end.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| URL path joining | `url + "/contact"` string concat | `urllib.parse.urljoin` | Handles trailing slashes, relative paths, scheme normalization |
| HTML link parsing | Regex on raw HTML bytes | `BeautifulSoup(html, 'lxml')` | Malformed HTML, different quote styles, whitespace in attributes |
| HTTP redirect following | Manual location header check + re-request | `httpx.Client(follow_redirects=True)` | Handles redirect chains, relative redirects, HTTP 301/302/307/308 |
| Timeout enforcement | `threading.Timer` or signal alarm | `httpx.Client(timeout=10.0)` | httpx implements per-request connect + read timeouts correctly |

**Key insight:** URL manipulation and HTML parsing each contain a long tail of edge cases that are fully solved by stdlib and BeautifulSoup. Custom implementations will fail on real-world sites within the first week.

---

## Common Pitfalls

### Pitfall 1: Accumulate-then-select vs. page-by-page selection

**What goes wrong:** Returning the first email found on each page rather than collecting all candidates and scoring at the end. A footer `info@` on the homepage would be returned when a `jobs@` on `/contact` would have been preferred.
**Why it happens:** Intuitive page-by-page early return.
**How to avoid:** Accumulate all email candidates from all pages visited so far, then call `_best_email()` once on the accumulated set. Return early only if a preferred-tier email is found.
**Warning signs:** Tests pass when preferred email is on page 1 but fail when it's only on page 3.

### Pitfall 2: httpx timeout semantics

**What goes wrong:** Setting `timeout=10` assumes that means "10 seconds total". In httpx the default `timeout` is a `Timeout` object with separate connect, read, write, and pool timeouts. `timeout=10.0` (a float) sets all four to 10 seconds.
**Why it happens:** Library documentation is nuanced.
**How to avoid:** Pass a plain float: `timeout=10.0`. This sets all timeout phases to 10 seconds, which is correct for this use case.
**Warning signs:** Requests complete but are slower than expected; or connect timeouts differ from read timeouts.

### Pitfall 3: Non-200 pages treated as failures

**What goes wrong:** A 404 on `/contact` throws an exception or stops the fallback chain. The spec says "a 404 on /contact means try /about next."
**Why it happens:** Confusing HTTP error status codes with network errors. httpx does NOT raise on 4xx/5xx by default (unlike `raise_for_status()`).
**How to avoid:** Only catch `httpx.TimeoutException` and `httpx.RequestError` for network failures. Check `resp.status_code == 200` to decide whether to parse, but let non-200 responses fall through to the next fallback path.
**Warning signs:** Test for 404 on /contact shows `scrape_failed` instead of trying /about.

### Pitfall 4: scrape_failed vs. no_email_found conflation

**What goes wrong:** Setting `no_email_found` even when all three pages timed out. These are different conditions with different diagnostic value.
**Why it happens:** Both conditions result in no email; easy to use one status for both.
**How to avoid:** Track `any_page_succeeded` boolean. Only set `no_email_found` if at least one page returned 200. Set `scrape_failed` if zero pages succeeded.
**Warning signs:** Logs show `no_email_found` for companies whose sites are down.

### Pitfall 5: Missing `Status.SCRAPE_FAILED` in models.py

**What goes wrong:** `scraper.py` imports `Status.SCRAPE_FAILED` but the enum member doesn't exist yet. Import error at runtime.
**Why it happens:** CONTEXT.md explicitly notes this addition is required but it's in a different file from the scraper.
**How to avoid:** Wave 0 of Phase 3 must add `SCRAPE_FAILED = "scrape_failed"` to the `Status` enum in `models.py` and update the existing `test_status_enum_values` test to include `"scrape_failed"` in the expected set.
**Warning signs:** `AttributeError: SCRAPE_FAILED` at import time; existing test `test_status_enum_values` would catch this if updated first.

### Pitfall 6: Email regex over-matching

**What goes wrong:** Regex matches version strings (`2.3@example`), image filenames, or other false positives that look like email addresses.
**Why it happens:** Simple email regex has many edge cases.
**How to avoid:** Use a reasonably strict regex: `[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}`. Validate the TLD is at least 2 characters. The priority scoring system will naturally filter noise (most false positives won't match priority prefixes and won't be selected if real emails exist).
**Warning signs:** Company records with emails like `2.0@changelog.md`.

### Pitfall 7: Base URL construction for fallback paths

**What goes wrong:** Using the original URL (which might include a path) as the base for `/contact`. Example: `https://example.com/en/` + urljoin `/contact` = `https://example.com/contact` (correct), but naive concatenation gives `https://example.com/en//contact`.
**Why it happens:** urljoin with absolute paths replaces the path correctly, but the base URL passed to urljoin must be the full original URL (not scheme+netloc alone) OR an absolute path `/contact` with scheme+netloc base.
**How to avoid:** Extract `scheme://netloc` from `urlparse` and use that as the base for fallback URLs: `urljoin(f"{parsed.scheme}://{parsed.netloc}", "/contact")`.
**Warning signs:** `/contact` resolves to unexpected paths in tests.

---

## Code Examples

### httpx synchronous client with all required options
```python
# Source: https://www.python-httpx.org/advanced/clients/
import httpx

with httpx.Client(
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"},
    timeout=10.0,
    follow_redirects=True,
) as client:
    response = client.get("https://example.com")
    if response.status_code == 200:
        html = response.text
```

### BeautifulSoup4 mailto: link extraction
```python
# Source: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, "lxml")
for tag in soup.find_all("a", href=True):
    if tag["href"].lower().startswith("mailto:"):
        email = tag["href"][7:].split("?")[0].strip().lower()
```

### Regex email extraction from page text
```python
import re

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# soup.get_text() strips HTML tags; regex runs on plain text
emails = _EMAIL_RE.findall(soup.get_text())
```

### pytest-httpx mock response
```python
# Source: https://pypi.org/project/pytest-httpx/ (v0.36.0)
import httpx

def test_scraper_homepage_email(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com",
        text='<a href="mailto:jobs@example.com">Contact</a>',
    )
    from job_mailer.scraper import scrape_company
    record = scrape_company("https://example.com")
    assert record.email_found == "jobs@example.com"
```

### Company name inference
```python
from urllib.parse import urlparse

def _infer_company_name(url: str) -> str:
    host = urlparse(url).hostname or ""
    host = host.removeprefix("www.")
    slug = host.split(".")[0]
    return slug.title()
```

### URL joining for fallback paths
```python
from urllib.parse import urlparse, urljoin

parsed = urlparse("https://example.com/some/path")
base = f"{parsed.scheme}://{parsed.netloc}"  # "https://example.com"
contact_url = urljoin(base, "/contact")       # "https://example.com/contact"
about_url   = urljoin(base, "/about")         # "https://example.com/about"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `requests` library | `httpx` (already in this project) | `httpx` 1.0 stable API; project chose httpx at scaffolding | `httpx` has identical sync API; adds async capability; CONTEXT.md mention of `requests` is superseded by pyproject.toml |
| `html.parser` (stdlib BS4 backend) | `lxml` (faster, already installed) | lxml >=6.0 | Speed; lxml is BS4's recommended fastest parser |

**Dependency note:** The CONTEXT.md says "use `requests` library". The pyproject.toml already declares `httpx` and does NOT declare `requests`. The research finding is: use `httpx`. The sync interface is identical for this use case and adding `requests` would create an unnecessary duplicate dependency.

---

## Open Questions

1. **Email obfuscation coverage**
   - What we know: STATE.md flags this — "Obfuscated email format coverage should be validated against a sample of real target URLs before finalizing normalization logic"
   - What's unclear: The percentage of target sites that use HTML entity encoding (`&#64;` for `@`), JS-based obfuscation, or `[at]` text substitution
   - Recommendation: The BeautifulSoup + regex approach handles standard plain text and mailto: links. HTML entities are decoded by BS4 automatically via `soup.get_text()`. For Phase 3, do not implement JS obfuscation decoding — it requires a headless browser (Playwright/Selenium), which is out of scope. Document this as a known limitation.

2. **httpx CONTEXT.md vs. pyproject.toml discrepancy**
   - What we know: CONTEXT.md says "use `requests`"; pyproject.toml already has `httpx` and no `requests`
   - What's unclear: Whether the user expects `requests` to be added
   - Recommendation: Do NOT add `requests`. Use `httpx` which is already installed. The sync API is equivalent. Flag this in PLAN.md for visibility.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already configured in pyproject.toml) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `addopts = "-x"`) |
| Quick run command | `uv run pytest tests/test_scraper.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DISC-01 | Extracts email from homepage mailto: link | unit | `uv run pytest tests/test_scraper.py::test_homepage_mailto_email -x` | Wave 0 |
| DISC-01 | Extracts email from homepage page text regex | unit | `uv run pytest tests/test_scraper.py::test_homepage_text_email -x` | Wave 0 |
| DISC-02 | Falls back to /contact when homepage has no email | unit | `uv run pytest tests/test_scraper.py::test_contact_fallback -x` | Wave 0 |
| DISC-03 | Falls back to /about when homepage and /contact have no email | unit | `uv run pytest tests/test_scraper.py::test_about_fallback -x` | Wave 0 |
| DISC-04 | Returns no_email_found when no email on any page | unit | `uv run pytest tests/test_scraper.py::test_no_email_found -x` | Wave 0 |
| DISC-04 | Returns scrape_failed when all pages error | unit | `uv run pytest tests/test_scraper.py::test_scrape_failed -x` | Wave 0 |
| (support) | Priority scoring: preferred beats deprioritized | unit | `uv run pytest tests/test_scraper.py::test_email_priority -x` | Wave 0 |
| (support) | Never-return addresses are excluded | unit | `uv run pytest tests/test_scraper.py::test_never_return_excluded -x` | Wave 0 |
| (support) | Company name inferred from domain slug | unit | `uv run pytest tests/test_scraper.py::test_company_name_inference -x` | Wave 0 |
| (support) | Status.SCRAPE_FAILED exists in Status enum | unit | `uv run pytest tests/test_models.py -x` | Update existing |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_scraper.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_scraper.py` — covers DISC-01 through DISC-04 and supporting priority/inference tests; requires `pytest-httpx` for httpx mocking
- [ ] `models.py` update — add `SCRAPE_FAILED = "scrape_failed"` to `Status` enum
- [ ] `tests/test_models.py` update — add `"scrape_failed"` to `expected_values` set in `test_status_enum_values`
- [ ] Install test dependency: `uv add --dev pytest-httpx`

---

## Sources

### Primary (HIGH confidence)
- [python-httpx.org/quickstart](https://www.python-httpx.org/quickstart/) — timeout float semantics, follow_redirects, headers
- [python-httpx.org/advanced/clients](https://www.python-httpx.org/advanced/clients/) — Client context manager, base_url, combined headers
- [BeautifulSoup 4.14.3 documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) — find_all, get_text, lxml parser recommendation
- [pyproject.toml in this repo] — confirmed httpx, beautifulsoup4, lxml already declared dependencies

### Secondary (MEDIUM confidence)
- [pytest-httpx PyPI v0.36.0](https://pypi.org/project/pytest-httpx/) — httpx_mock fixture, add_response usage, sync support confirmed
- [urllib.parse stdlib docs](https://docs.python.org/3/library/urllib.parse.html#urllib.parse.urljoin) — urljoin behavior with absolute paths

### Tertiary (LOW confidence)
- [scrapehero.com email scraping guide](https://www.scrapehero.com/scrape-emails-from-website/) — dual-source extraction pattern (verified against BS4 docs)
- [WebSearch: obfuscated email formats] — HTML entity encoding decoded by BS4; JS obfuscation out of scope

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pyproject.toml is the ground truth; httpx/bs4/lxml already declared
- Architecture: HIGH — patterns verified against official httpx and BS4 docs
- Pitfalls: HIGH — httpx timeout semantics and scrape_failed/no_email_found distinction verified against official docs and spec

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (httpx and BS4 are stable; pytest-httpx at 0.36.0 may update)
