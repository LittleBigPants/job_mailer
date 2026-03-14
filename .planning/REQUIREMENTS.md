# Requirements: job-mailer

**Defined:** 2026-03-14
**Core Value:** A single command turns a CSV of company URLs into a batch of personalized, human-sounding cold emails, eliminating the repetitive work of finding contacts and writing intros.

## v1 Requirements

### Infrastructure

- [ ] **INFRA-01**: Project includes README documentation for required DNS auth setup (SPF/DKIM/DMARC) before any live sends
- [ ] **INFRA-02**: API keys (GROQ_API_KEY, RESEND_API_KEY, RESEND_FROM_EMAIL) are loaded from .env via python-dotenv; .env is gitignored from project setup
- [ ] **INFRA-03**: profile.toml has a locked schema with a profile.example.toml committed to the repo

### Input

- [ ] **INPUT-01**: Tool reads company URLs from a single-column CSV file specified via CLI argument

### Discovery

- [ ] **DISC-01**: Scraper extracts contact email from homepage via mailto: link parsing and regex pattern matching on full page text
- [ ] **DISC-02**: If no email found on homepage, falls back to /contact page using same extraction logic
- [ ] **DISC-03**: If no email found on /contact, falls back to /about page using same extraction logic
- [ ] **DISC-04**: If no email found after all three pages, logs status as 'no_email_found' and continues to next company without stopping the run

### Generation

- [ ] **GEN-01**: Tool infers company name and industry from the domain URL and passes both to the LLM
- [ ] **GEN-02**: Groq LLM generates a personalized email intro (target: 60–180 words) using developer profile loaded from profile.toml
- [ ] **GEN-03**: Generated message is validated before send — rejected and retried once if: outside 60–180 words, contains [bracket] placeholders, or matches cliché deny-list ("I hope this finds you", "quick question", "synergy", "touch base", "circle back")
- [ ] **GEN-04**: If validation fails after one retry, company is logged as 'generation_failed' and skipped

### Sending

- [ ] **SEND-01**: Sends email via Resend API using credentials from .env
- [ ] **SEND-02**: Inspects Resend response object for named error types (429 rate limit, daily_quota_exceeded, invalid_email) — not just HTTP status code
- [ ] **SEND-03**: Configurable delay between sends (default: 2s; configurable via profile.toml or --delay CLI flag)
- [ ] **SEND-04**: --dry-run flag causes the tool to scrape and generate messages but never call the Resend API

### Logging

- [ ] **LOG-01**: Append-only CSV log is written immediately after each company attempt (before moving to next row)
- [ ] **LOG-02**: Log captures: url, company_name, email_found, generated_message, status, resend_message_id, timestamp
- [ ] **LOG-03**: On re-run, URLs where status=sent in the existing log are skipped (idempotent re-runs)

## v2 Requirements

### Safety Controls

- **SAFE-01**: --limit N flag hard-stops the run after N emails sent in a single invocation

### UX

- **UX-01**: --preview flag prints each generated message to stdout for review before confirming send
- **UX-02**: Run summary printed on completion: X sent, Y skipped (already sent), Z failed (no email / generation failed)

## Out of Scope

| Feature | Reason |
|---------|--------|
| LinkedIn / meta tag / social scraping | Fragile, legally risky, out of scope for personal tool |
| /about page content for personalization | Industry inferred from domain; extra scraping adds complexity without clear gain |
| Reply tracking or follow-up scheduling | Not a CRM; personal tool with no persistent state beyond the log |
| Web UI or multi-user support | Single-user personal CLI |
| OAuth or any authentication layer | No auth needed for a personal local tool |
| Email guessing (firstname@company.com patterns) | Unverified guesses hurt deliverability and domain reputation |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Pending |
| INFRA-02 | Phase 1 | Pending |
| INFRA-03 | Phase 1 | Pending |
| INPUT-01 | Phase 2 | Pending |
| DISC-01 | Phase 3 | Pending |
| DISC-02 | Phase 3 | Pending |
| DISC-03 | Phase 3 | Pending |
| DISC-04 | Phase 3 | Pending |
| GEN-01 | Phase 4 | Pending |
| GEN-02 | Phase 4 | Pending |
| GEN-03 | Phase 4 | Pending |
| GEN-04 | Phase 4 | Pending |
| SEND-01 | Phase 5 | Pending |
| SEND-02 | Phase 5 | Pending |
| SEND-03 | Phase 5 | Pending |
| SEND-04 | Phase 6 | Pending |
| LOG-01 | Phase 5 | Pending |
| LOG-02 | Phase 5 | Pending |
| LOG-03 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-14*
*Last updated: 2026-03-14 after roadmap creation*
