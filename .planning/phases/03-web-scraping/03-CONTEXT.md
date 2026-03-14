# Phase 3: Web Scraping - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Given a company URL, discover a contact email or report clearly why none was found. Scope: HTTP requests to up to three pages (homepage → /contact → /about), email extraction and prioritization, company name inference from domain slug, and error handling. LLM inference, email generation, and sending are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Email Selection
- Collect all email candidates from both mailto: links and page text (regex), then score by priority list — best address wins regardless of source
- Priority order (highest to lowest):
  1. Preferred: jobs@, hiring@, contact@, hello@, hi@, team@
  2. Deprioritized (use if nothing better found): info@, admin@, support@
  3. Never return: noreply@, no-reply@, mailer@, donotreply@
- If only never-return addresses are found across all three pages: treat as no_email_found
- If only deprioritized addresses are found and no preferred match: return the first deprioritized address found

### Network Error Handling
- Per-page timeout: 10 seconds
- No retries — log a warning and skip the page; treat as "no email found on this page"
- Continue the fallback chain even if one page errors (a 404 on /contact means try /about next)
- If ALL three pages fail (connection errors, timeouts, all non-200): log status as `scrape_failed` (distinct from `no_email_found`)
- `scrape_failed` requires adding a new `Status.SCRAPE_FAILED` enum value to `models.py`

### Anti-bot / Request Headers
- Use `requests` library (synchronous, battle-tested; pipeline is sequential)
- Send a realistic Chrome-like User-Agent header on all requests
- Follow HTTP redirects automatically (requests default behavior)
- No delay between page requests within a single company (inter-company delay already handled by profile.toml / --delay flag)

### Company Name Inference
- Derived from domain slug (e.g. `stripe.com` → "Stripe")
- Claude's discretion on how to handle acronyms or compound names — simple title-case of slug is acceptable baseline

### Claude's Discretion
- HTML parsing library choice (BeautifulSoup vs regex-only for link extraction)
- Exact User-Agent string to use
- Module structure (e.g. `scraper.py` module name and function signatures)
- How to build fallback page URLs from the base domain (URL joining logic)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CompanyRecord` (models.py): has `url`, `company_name`, `email_found`, `status` fields — the scraper populates these directly
- `Status` enum (models.py): `NO_EMAIL_FOUND` already defined; `SCRAPE_FAILED` needs to be added
- `__main__.py`: clean stub at "Config loaded. Input file: {input}" — Phase 3 logic plugs in here

### Established Patterns
- `sys.exit()` with actionable messages for fatal errors (config.py pattern)
- No async — synchronous pipeline throughout; `requests` fits naturally

### Integration Points
- Scraper function should accept a URL string and return a populated `CompanyRecord`
- `__main__.py` will call the scraper per row after reading the CSV (Phase 3 adds CSV reading + scraper loop)

</code_context>

<specifics>
## Specific Ideas

- Priority list for email selection is explicit and ordered: jobs@/hiring@ > contact@/hello@/hi@/team@ > info@/admin@/support@ > (skip noreply/mailer variants)
- `scrape_failed` status distinguishes "site unreachable" from "site reachable but no email" — useful for log analysis

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-web-scraping*
*Context gathered: 2026-03-14*
