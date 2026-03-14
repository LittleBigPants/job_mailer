# Roadmap: job-mailer

## Overview

job-mailer is built in six phases that follow the natural dependency order of its pipeline. Infrastructure and secrets safety come first because two critical pitfalls (API keys in git, sending from an unauthenticated domain) cannot be retrofitted cheaply. The data model and config loading come next because every downstream stage depends on them. Then each pipeline stage is built and verified in isolation — scraper, generator, sender+logger — before the orchestrator wires them together. The final phase integrates the full end-to-end loop with dry-run, idempotency, and a working CLI entry point.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Scaffolding** - Secure project skeleton with secrets management, DNS auth docs, and developer profile schema (completed 2026-03-14)
- [ ] **Phase 2: Data Model and Config** - CompanyRecord dataclass, ProfileConfig loader, and stub CLI that validates config on startup
- [ ] **Phase 3: Web Scraping** - Email discovery via footer/contact/about fallback chain with company name inference
- [ ] **Phase 4: LLM Generation** - Groq-powered personalized email generation with post-generation validation
- [ ] **Phase 5: Sending and Logging** - Resend email delivery with error inspection and append-only per-company CSV log
- [ ] **Phase 6: Orchestration and CLI** - Full pipeline wired end-to-end with dry-run, idempotency, send delay, and Typer CLI

## Phase Details

### Phase 1: Scaffolding
**Goal**: The project is safe to develop — secrets cannot be accidentally committed, the developer profile schema is locked, and DNS authentication is documented before any live send occurs
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03
**Success Criteria** (what must be TRUE):
  1. Running `git status` after project init shows `.env` is gitignored and never appears as a tracked file
  2. `profile.example.toml` is committed to the repo and documents every required field with types and example values
  3. The README contains a DNS setup section (SPF/DKIM/DMARC) that a developer can follow before any live send
  4. `python-dotenv` loads `GROQ_API_KEY`, `RESEND_API_KEY`, and `RESEND_FROM_EMAIL` from `.env` at startup; missing keys produce a clear error, not a traceback
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md — Project skeleton: pyproject.toml, .gitignore, src/job_mailer package, .env.example
- [ ] 01-02-PLAN.md — Config module + tests: check_env() and load_profile() via TDD
- [ ] 01-03-PLAN.md — Profile schema + DNS docs: profile.example.toml and README DNS setup section

### Phase 2: Data Model and Config
**Goal**: The shared data contract and config loading are in place, making every downstream stage independently testable before any external service is called
**Depends on**: Phase 1
**Requirements**: INPUT-01
**Success Criteria** (what must be TRUE):
  1. `CompanyRecord` dataclass exists with all required fields (url, company_name, email_found, generated_message, status, resend_message_id, timestamp) and all valid status values defined
  2. `config.py` loads `profile.toml`, validates all required fields, and raises a clear error (not a KeyError) when a field is missing
  3. The stub CLI accepts `--input <csv>` and exits cleanly after loading and validating config, before any pipeline logic runs
**Plans**: TBD

### Phase 3: Web Scraping
**Goal**: Given a company URL, the tool can reliably discover a contact email or report a clear reason why none was found
**Depends on**: Phase 2
**Requirements**: DISC-01, DISC-02, DISC-03, DISC-04
**Success Criteria** (what must be TRUE):
  1. Given a URL where a contact email is in the homepage footer, the scraper returns that email on the first request without falling back
  2. Given a URL with no email on the homepage but one on `/contact`, the scraper returns the `/contact` email after one fallback
  3. Given a URL with no email on homepage or `/contact` but one on `/about`, the scraper returns the `/about` email
  4. Given a URL with no discoverable email on any of the three pages, the scraper logs status `no_email_found` and the run continues to the next company without stopping
  5. Company name is inferred from the domain slug (e.g. `stripe.com` → "Stripe") and stored on the record
**Plans**: TBD

### Phase 4: LLM Generation
**Goal**: Given a company record and developer profile, the tool produces a personalized, send-ready email intro that passes validation — or skips the company with a clear status if it cannot
**Depends on**: Phase 3
**Requirements**: GEN-01, GEN-02, GEN-03, GEN-04
**Success Criteria** (what must be TRUE):
  1. The generated message is between 60 and 180 words for a representative sample of diverse company domains
  2. A message containing `[bracket]` placeholders is rejected on first validation and retried; if the retry also fails, the company is logged as `generation_failed` and skipped
  3. A message matching a cliché opener from the deny-list ("I hope this finds you", "quick question", "synergy", "touch base", "circle back") is rejected and retried once before the company is skipped
  4. The Groq model name is driven by a config key so it can be changed without modifying code
**Plans**: TBD

### Phase 5: Sending and Logging
**Goal**: The tool can send an email via Resend and immediately write a complete log record — whether the send succeeded, failed, or hit a rate limit
**Depends on**: Phase 4
**Requirements**: SEND-01, SEND-02, SEND-03, LOG-01, LOG-02
**Success Criteria** (what must be TRUE):
  1. A successful send writes one row to the CSV log immediately (not after all rows), with all seven fields populated: url, company_name, email_found, generated_message, status, resend_message_id, timestamp
  2. A Resend 429 rate-limit response is detected from the response object's error field (not HTTP status code) and results in a log row with status `rate_limited`, not `sent`
  3. A `daily_quota_exceeded` error from Resend produces a clear terminal message and graceful exit, not a traceback
  4. Send delay between emails defaults to 2 seconds and is configurable via `profile.toml` or `--delay` CLI flag
**Plans**: TBD

### Phase 6: Orchestration and CLI
**Goal**: A single CLI command reads a CSV of company URLs and drives the full pipeline end-to-end — with dry-run safety, skip-already-sent idempotency, and per-row error isolation
**Depends on**: Phase 5
**Requirements**: SEND-04, LOG-03
**Success Criteria** (what must be TRUE):
  1. Running with `--dry-run` scrapes and generates messages for all companies but makes zero calls to the Resend API; generated messages appear in the log with status `dry_run`
  2. On a second run against the same CSV, companies where `status=sent` already exists in the log are skipped without re-sending
  3. A scrape failure or generation failure for one company does not abort the run — the tool continues to the next company and logs the failure
  4. The CLI provides `--input`, `--dry-run`, and `--delay` flags and exits with a non-zero code when config is invalid or required flags are missing
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Scaffolding | 3/3 | Complete   | 2026-03-14 |
| 2. Data Model and Config | 0/TBD | Not started | - |
| 3. Web Scraping | 0/TBD | Not started | - |
| 4. LLM Generation | 0/TBD | Not started | - |
| 5. Sending and Logging | 0/TBD | Not started | - |
| 6. Orchestration and CLI | 0/TBD | Not started | - |
