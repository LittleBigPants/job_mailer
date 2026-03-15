# job-mailer

## What This Is

A Python CLI tool that automates cold email outreach for a fullstack developer's job search. Given a CSV of company URLs, it scrapes contact emails from pages via a multi-page fallback chain, generates a short personalized intro via Groq LLM, and sends it via Resend — logging every outcome with dry-run safety and idempotent re-runs.

## Core Value

A single command turns a CSV of company URLs into a batch of personalized, human-sounding cold emails, eliminating the repetitive work of finding contacts and writing intros.

## Requirements

### Validated

- ✓ Read company URLs from a single-column CSV file — v1.0
- ✓ Scrape contact email from homepage footer → /contact → /about; log 'no_email_found' if none found — v1.0
- ✓ Infer company name and industry from domain/URL — v1.0
- ✓ Load developer profile from profile.toml (name, stack, years experience, target role, links) — v1.0
- ✓ Generate 60–180 word personalized intro via Groq LLM — no placeholders, no clichés — v1.0
- ✓ Send email via Resend API with named error inspection (429, quota, invalid_email) — v1.0
- ✓ Log full record per company: url, company_name, email_found, generated_message, status, resend_message_id, timestamp — v1.0
- ✓ Configurable delay between sends via profile.toml or --delay CLI flag — v1.0
- ✓ --dry-run flag: scrape + generate but do not send; log status dry_run — v1.0
- ✓ Idempotent re-runs: skip already-sent URLs (status=sent in existing log) — v1.0
- ✓ API keys and RESEND_FROM_EMAIL loaded from .env via python-dotenv; .env gitignored — v1.0
- ✓ profile.example.toml with locked schema committed to repo — v1.0
- ✓ README documents DNS auth setup (SPF/DKIM/DMARC) before any live send — v1.0

### Active

*(No active requirements — see /gsd:new-milestone to define v1.1)*

### Out of Scope

- Scraping /about for company description — industry inferred from domain only (keeps requests minimal)
- LinkedIn, meta tag, or social scraping for email discovery — fragile, legally risky
- Reply tracking or follow-up scheduling — personal tool, not a CRM
- Web UI or multi-user support — single-user personal CLI
- Email guessing (firstname@company.com patterns) — unverified guesses hurt deliverability
- --limit N flag (hard-stop after N emails) — deferred to v1.1
- --preview flag (print messages before confirming send) — deferred to v1.1
- Run summary printed on completion — deferred to v1.1

## Context

- v1.0 shipped 2026-03-15: 6 phases, 18 plans, 1,888 LOC Python
- Tech stack: Python 3.x, Typer (CLI), httpx + BeautifulSoup (scraping), Groq SDK (LLM), Resend SDK (email), python-dotenv, tomllib, pytest, ruff
- APIs: Groq (LLM generation), Resend (email delivery)
- Developer profile is a one-time config file (profile.toml) edited by the user
- Personal tool — no auth, no multi-tenancy, no database
- All 19 v1 requirements shipped and validated

## Constraints

- **Tech**: Python CLI (no web framework)
- **LLM**: Groq API — must use Groq, not OpenAI or local model
- **Email**: Resend API — no SMTP fallback
- **Input**: Single-column CSV of URLs, no preprocessing required from user
- **Config**: Developer profile in `profile.toml`, read at runtime

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Industry inferred from domain, not scraped | Avoids extra HTTP requests; LLM is good enough at domain→industry inference | ✓ Good — worked well in generation |
| Email fallback: footer → /contact → /about only | Keeps scraper simple and fast; LinkedIn scraping is fragile and risky | ✓ Good — clean three-page chain |
| Config file for developer profile (profile.toml) | Write once, reuse across runs; cleaner than flags | ✓ Good — tomllib reads locked schema |
| Both --dry-run flag and send delay | Safety defaults; prevents accidental spam blasts | ✓ Good — essential for safe testing |
| Status enum with named values | Explicit outcomes (sent, rate_limited, no_email_found, generation_failed, dry_run) make log analysis straightforward | ✓ Good — clean log structure |
| Append-only CSV log with immediate per-row writes | Crash-safe; re-runs can pick up where left off via idempotency check | ✓ Good — enables reliable reruns |
| sys.exit() on config errors (not raise) | Human-readable error messages instead of raw tracebacks | ✓ Good — UX improvement |
| load_dotenv() at module top-level | Prevents intermittent missing-key bugs when other modules read env first | ✓ Good — required pattern |

---
*Last updated: 2026-03-15 after v1.0 milestone*
