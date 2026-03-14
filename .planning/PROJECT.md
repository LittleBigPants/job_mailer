# job-mailer

## What This Is

A Python CLI tool that automates cold email outreach for a fullstack developer's job search. Given a CSV of company URLs, it scrapes contact emails from pages, generates a short personalized intro via Groq LLM, and sends it via Resend — logging every outcome.

## Core Value

A single command turns a CSV of company URLs into a batch of personalized, human-sounding cold emails, eliminating the repetitive work of finding contacts and writing intros.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Read company URLs from a single-column CSV file
- [ ] Scrape contact email from homepage footer → /contact → /about (in that order); log 'no_email_found' if none found
- [ ] Infer company name and industry from domain/URL (no about-page scraping)
- [ ] Load developer profile from a config file (profile.toml: name, stack, years experience, target role, links)
- [ ] Generate 60–180 word personalized intro via Groq LLM — specific to company, no placeholders, no clichés
- [ ] Send email via Resend API
- [ ] Log full record per company: url, company_name, email_found, generated_message, status, resend_message_id, timestamp
- [ ] Configurable delay between sends (avoid spam signals)
- [ ] --dry-run flag: scrape + generate but do not send

### Out of Scope

- Scraping /about for company description — industry inferred from domain only (keeps requests minimal)
- LinkedIn, meta tag, or social scraping for email discovery
- Reply tracking or follow-up scheduling — personal tool, not a CRM
- Web UI or multi-user support

## Context

- Greenfield Python CLI project in the `job_mailer` repo
- APIs in use: Groq (LLM generation), Resend (email delivery)
- Developer profile is a one-time config file edited by the user
- Personal tool — no auth, no multi-tenancy, no database needed
- Company name derived from domain (e.g. `stripe.com` → "Stripe"); LLM infers industry from the same signal

## Constraints

- **Tech**: Python CLI (no web framework)
- **LLM**: Groq API — must use Groq, not OpenAI or local model
- **Email**: Resend API — no SMTP fallback
- **Input**: Single-column CSV of URLs, no preprocessing required from user
- **Config**: Developer profile in `profile.toml` (or `.toml` equivalent), read at runtime

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Industry inferred from domain, not scraped | Avoids extra HTTP requests; LLM is good enough at domain→industry inference | — Pending |
| Email fallback: footer → /contact → /about only | Keeps scraper simple and fast; LinkedIn scraping is fragile and risky | — Pending |
| Config file for developer profile | Write once, reuse across runs; cleaner than flags | — Pending |
| Both dry-run flag and send delay | Safety defaults; prevents accidental spam blasts | — Pending |

---
*Last updated: 2026-03-14 after initialization*
