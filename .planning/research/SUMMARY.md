# Project Research Summary

**Project:** job_mailer
**Domain:** Python CLI cold email outreach pipeline — web scraping, LLM generation, transactional email
**Researched:** 2026-03-14
**Confidence:** HIGH

## Executive Summary

job_mailer is a personal developer tool that automates cold outreach for job searching. It reads a CSV of company URLs, scrapes each homepage for a contact email, generates a personalized intro message via Groq's LLM API, and sends it through Resend — all from a single CLI command. The standard build pattern for this class of tool is a linear stage pipeline: each company flows through scraper → generator → sender → logger as a typed `CompanyRecord` dataclass. Research confirms this pattern is well-documented, all recommended libraries have stable official SDKs, and the architecture has clear component boundaries that make each stage independently testable. The recommended stack (Typer, httpx, BeautifulSoup + lxml, groq SDK, resend SDK, tenacity) is a tight, idiomatic fit with no unnecessary dependencies.

The primary risks are not technical — they are operational. Three pitfalls stand above all others: (1) sending from your primary email domain without DNS authentication, which can permanently damage your inbox reputation; (2) skipping per-email idempotent logging, which causes duplicate sends if the run is interrupted and restarted; and (3) shipping LLM-generated messages without post-generation validation, which allows clichés, bracket placeholders, and fabricated company facts to reach real recipients. These risks are cheap to mitigate if addressed at design time but expensive to recover from after the fact.

The build order prescribed by architecture research directly mirrors the mitigation strategy for these pitfalls: scaffold secrets management and DNS setup before writing any code, implement the `CompanyRecord` model and append-only logger early, and treat LLM output validation as a first-class feature rather than a post-launch addition. An MVP covering the full pipeline — CSV in, scrape, generate, send, log — is achievable in a focused build. Differentiating features (idempotent run guard, `--preview` flag, configurable model) are well-scoped v1.x additions once the core loop is validated.

## Key Findings

### Recommended Stack

The stack is entirely composed of official SDKs and well-maintained Python packages, all version-confirmed against PyPI as of the research date. Python 3.11+ is the minimum floor (required by `tomllib` stdlib and sensible given the Groq SDK's 3.10 floor). The dependency footprint is intentionally lean: no pandas, no playwright, no SMTP configuration, no browser automation.

**Core technologies:**
- Python 3.11+: runtime — sets the floor for `tomllib` stdlib TOML parsing; no extra dependency for config
- Typer 0.24.1: CLI framework — type-hint-driven, auto-generates `--help`, `--dry-run` and `--delay` map cleanly to typed params
- httpx 0.28.1: HTTP client — sync + async in one package; shared with Groq SDK internally, so not an extra dependency
- beautifulsoup4 4.14.3 + lxml 6.0.2: HTML parsing — industry standard; tolerates malformed HTML; lxml backend for performance
- groq 1.1.1: LLM API client — official SDK; OpenAI-compatible interface; sync and async
- resend 2.23.0: email delivery — single-call API; no SMTP configuration; returns error objects, does not throw on 429
- tenacity 9.1.4: retry logic — decorator-based exponential backoff for httpx and API call sites
- tomllib (stdlib): config parsing — read-only; zero extra dependency on Python 3.11+
- python-dotenv: secrets loading — loads `GROQ_API_KEY` and `RESEND_API_KEY` from `.env`; keeps secrets out of committed files

### Expected Features

The feature set has a clean P1/P2/P3 split with no ambiguity at the MVP level. The nine P1 features form a complete, runnable pipeline. P2 features (idempotency, preview, model selection) are low-cost additions that should be scheduled immediately after MVP validation. P3 features are deferred.

**Must have (table stakes — v1 launch):**
- CSV input parsing (single-column URLs, skip blanks)
- Email discovery via footer → /contact → /about fallback chain with regex + mailto extraction
- Company name inference from domain slug
- Developer profile loaded from `profile.toml` (name, stack, years, role, links)
- Groq LLM message generation with 60–180 word constraint and no-cliché prompt guard
- Send via Resend API with error object inspection
- Per-company CSV log (url, company_name, email_found, generated_message, status, resend_message_id, timestamp)
- `--dry-run` flag that skips send but logs `status=dry_run`
- Configurable send delay (config key, no zero-second default)

**Should have (v1.x — add after core loop validated):**
- Idempotent run guard — skip already-sent URLs by reading existing log; prevents duplicate sends on restart
- `--preview` flag — prints message table to stdout without sending; enables prompt quality review
- `no_email_found` end-of-run summary — surfaces which companies had no discoverable email
- Configurable LLM model selection — `groq_model` config key; easy to swap without code changes

**Defer (v2+):**
- Message approval gate (`--confirm` interactive mode) — useful but adds friction; defer until prompt quality is trusted
- Follow-up batch generation for non-responders — requires workflow understanding built from actual use
- JSONL/SQLite output formats — defer until CSV proves insufficient

**Anti-features (do not build):**
- LinkedIn/social scraping — ToS risk, fragile, disproportionate complexity
- Reply/open tracking — requires infrastructure that turns a CLI into a mini-CRM
- Email guessing by name pattern — bounce rate above 2% damages domain reputation
- Web UI or SMTP fallback — out of scope per project constraints

### Architecture Approach

The canonical architecture is a linear stage pipeline with a shared `CompanyRecord` dataclass as the data contract. Each stage is a separate module with a single responsibility, wired together by a thin `orchestrator.py`. The CLI entry point (`cli.py`) parses flags and calls `orchestrator.run()`; all business logic lives in the orchestrator and stage modules. The orchestrator wraps each row in `try/except`, logs errors and continues — the batch never aborts on a single failure. The append-only log CSV serves as both the audit trail and the resumability mechanism.

**Major components:**
1. `models.py` — `CompanyRecord` dataclass; the shared data contract all stages accept and return
2. `config.py` — loads and validates `profile.toml`; exposes typed `ProfileConfig` object
3. `scraper.py` — HTTP GET with httpx + BeautifulSoup; footer → /contact → /about fallback; email extraction
4. `generator.py` — builds Groq prompt from `CompanyRecord` + `ProfileConfig`; calls Groq API; returns message text
5. `sender.py` — calls Resend API; no-ops in `dry_run` mode; inspects response object for error field
6. `logger.py` — appends one row to log CSV per company in `finally` block; guarantees write on error too
7. `orchestrator.py` — reads CSV, builds skip set from existing log, drives per-row loop with delay and error handling
8. `cli.py` — Typer entry point; thin wrapper around orchestrator; parses `--dry-run`, `--input`, `--delay`

**Build order (from ARCHITECTURE.md):** models → config → scraper → generator → sender → logger → orchestrator → cli. Each component is testable before the next is wired in.

### Critical Pitfalls

1. **Sending from primary domain without DNS authentication** — use a dedicated subdomain (e.g., `outreach.yourdomain.com`); configure SPF, DKIM, DMARC in Resend before writing a single line of send logic. Recovery cost: HIGH.

2. **Accidental email blast / no idempotency** — write one log entry per email immediately after send (in the `finally` block); on restart, read the log and skip `status=sent` rows. Never default `send_delay_seconds` to 0 or omit it from config. Recovery cost: MEDIUM to HIGH.

3. **LLM output with clichés, placeholders, or fabricated facts** — add post-generation validation: check for bracket patterns (`\[.*?\]`), enforce word count bounds, maintain a deny-list of cliché openers. Set `temperature <= 0.2`. Test against 10+ diverse domains including obscure ones before any live send. Recovery cost: MEDIUM (cannot unsend).

4. **Scraper silent failures on protected or JS-heavy pages** — log HTTP status code, page size, and specific failure reason as distinct fields, not just `no_email_found`. Handle obfuscated email formats (`[at]`, `(at)`, HTML entities). Set a realistic User-Agent string. Recovery cost: LOW (data loss, not reputation damage).

5. **API keys committed to the repository** — establish `.gitignore` (covering `.env`) on day one before any files are created; load `GROQ_API_KEY` and `RESEND_API_KEY` exclusively from environment variables; `profile.toml` must never contain key fields. Recovery cost: HIGH (requires key rotation and git history purge).

6. **Resend 429 errors silently logged as success** — inspect the Resend response object for the `error` field explicitly; handle `rate_limited` and `daily_quota_exceeded` as distinct cases with graceful exit messages. Recovery cost: LOW if caught; MEDIUM if already sent duplicates or false-sent records accumulate.

## Implications for Roadmap

Based on research, the pitfall-to-phase mapping and the architecture build order together prescribe a natural phase structure. The ordering is driven by two hard constraints: secrets and DNS must precede all API integration, and the data model and logger must precede idempotency logic.

### Phase 1: Project Scaffolding and Infrastructure

**Rationale:** Two of the six critical pitfalls (API keys in git, sending from primary domain) must be prevented before any code runs. These are infrastructure concerns, not features. Fixing them after the fact is expensive.
**Delivers:** Secure project skeleton — `pyproject.toml`, `.gitignore`, `.env` template, `profile.toml` schema, Resend subdomain verified with SPF/DKIM/DMARC, virtual environment with pinned dependencies.
**Addresses:** `profile.toml` config loading, developer profile schema definition, secrets separation.
**Avoids:** API keys committed to repo (Pitfall 5), domain reputation damage from unauthenticated sends (Pitfall 1).

### Phase 2: Core Data Model and Configuration

**Rationale:** `models.py` and `config.py` have no external dependencies and define the contracts everything else depends on. Building them first makes all downstream stages testable in isolation — this is the architecture's explicit build order recommendation.
**Delivers:** `CompanyRecord` dataclass with all status values, `ProfileConfig` object with validation, `config.py` with fast-fail on missing keys, basic CLI skeleton (`cli.py`) that loads config and exits cleanly.
**Implements:** `models.py`, `config.py`, stub `cli.py`.
**Avoids:** Hardcoding developer profile in generator (Architecture Anti-Pattern 5), passing dicts between stages (Architecture Anti-Pattern 1).

### Phase 3: Web Scraping

**Rationale:** Scraping is the first stage of the pipeline and has no dependency on the LLM or email services. It can be built and tested against real URLs before any API keys are needed. The scraper's logging schema must be designed correctly here — retrospectively adding HTTP status codes and failure reason fields to `CompanyRecord` would break the logger schema.
**Delivers:** `scraper.py` with footer → /contact → /about fallback chain; regex + mailto extraction; obfuscated email normalization (`[at]`, `(at)`, HTML entities); realistic User-Agent; distinct failure codes (blocked vs. absent vs. error); company name inference from domain slug.
**Uses:** httpx 0.28.1, beautifulsoup4 4.14.3 + lxml 6.0.2, tenacity for retry on transient HTTP errors.
**Avoids:** Silent scrape failures logged as `no_email_found` (Pitfall 4), no User-Agent triggering bot detection.

### Phase 4: LLM Message Generation

**Rationale:** Generator depends on `models.py` and `config.py` (both complete) but not on scraper output — it can be developed and tested with a mock `CompanyRecord`. Treating output validation as part of this phase (not a later addition) is the single most important quality decision in the project.
**Delivers:** `generator.py` with structured Groq prompt (role, developer profile context, company context, format constraints); post-generation validation (bracket placeholder detection, word count check, cliché opener deny-list); `temperature <= 0.2`; `groq_model` config key with sensible default.
**Uses:** groq 1.1.1 SDK, `ProfileConfig` from `config.py`.
**Avoids:** LLM clichés and placeholder leakage reaching live recipients (Pitfall 3), fabricated facts about companies.

### Phase 5: Email Sending and Logging

**Rationale:** Sending depends on all prior stages. The logger and sender must be designed together because the per-email log write in the `finally` block is what enables idempotency. These two components are co-dependent by design.
**Delivers:** `sender.py` with Resend API call, explicit `error` field inspection, `rate_limited` and `daily_quota_exceeded` handling, no-op in `dry_run` mode; `logger.py` with append-only CSV write in `finally` block.
**Uses:** resend 2.23.0 SDK, stdlib `csv.DictWriter`.
**Avoids:** Resend 429 silent failures (Pitfall 6), accidental blast from missing per-email logging (Pitfall 2).

### Phase 6: Pipeline Orchestration and CLI

**Rationale:** Orchestrator is the last component because it wires all stages — it can only be built once all stages exist. This is also where idempotency (skip-already-sent), the `--dry-run` flag behavior, configurable delay, and per-row error handling are implemented.
**Delivers:** `orchestrator.py` with CSV read, skip-set construction from existing log, per-row try/except loop with delay, `--dry-run` mode, progress output per company; `cli.py` as the public Typer interface with `--dry-run`, `--input`, `--delay` flags; end-to-end integration test with real or mocked services.
**Implements:** All architecture patterns — linear pipeline, continue-on-error, append-only log as state store.
**Avoids:** Business logic in CLI entry point (Architecture Anti-Pattern 2), batch abort on single row error (Anti-Pattern 3), in-memory-only state (Anti-Pattern 4).

### Phase 7: Polish and v1.x Features

**Rationale:** Once the core pipeline is validated end-to-end with a real dry-run, add the features that improve daily usability without changing the core data flow.
**Delivers:** `--preview` flag printing message table to stdout; `no_email_found` summary at end of run; run summary stats (sent, failed, skipped, no_email counts); UX improvements (progress line per company, actionable error messages for missing `profile.toml`).
**Addresses:** P2 features from FEATURES.md, UX pitfalls from PITFALLS.md (silent no-email, frozen-looking runs, dry-run output only in logs).

### Phase Ordering Rationale

- Infrastructure before code because two critical pitfalls (secrets, DNS) are impossible to retrofit cheaply.
- Data model before all stages because `CompanyRecord` is the contract everything else depends on — changing it later requires touching every stage.
- Scraper before generator/sender because it defines the failure taxonomy baked into `CompanyRecord.status`; that schema must be stable before the logger is finalized.
- Sender and logger in the same phase because their co-design (logger in `finally` block) is what makes idempotency possible.
- Orchestrator last because it wires all stages and can only be properly integrated once all stages are independently verified.

### Research Flags

Phases likely needing deeper research during planning:

- **Phase 3 (Scraping):** Obfuscated email formats vary widely in the wild; the research lists common patterns but real-world coverage should be validated against a sample of actual target company URLs before finalizing the normalization logic.
- **Phase 4 (LLM Generation):** Groq model availability and rate limits change; the recommended model (`llama-3.3-70b-versatile`) should be confirmed against the current Groq console before implementation. Prompt engineering for diverse company types may need iteration.

Phases with standard patterns (skip research-phase):

- **Phase 1 (Scaffolding):** Standard Python project setup; Resend DNS documentation is clear and official.
- **Phase 2 (Data Model):** Pure Python dataclasses with no external dependencies.
- **Phase 5 (Sending/Logging):** Resend SDK and stdlib csv are well-documented; error handling patterns are fully specified in PITFALLS.md.
- **Phase 6 (Orchestration):** Linear pipeline with try/except loop is a canonical pattern; well-documented in ARCHITECTURE.md with code examples.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI official pages; no speculation; version compatibility matrix fully checked |
| Features | HIGH | Project requirements are explicit; domain patterns (cold email, scraping) are well-established; competitor analysis corroborates feature set |
| Architecture | HIGH | Linear pipeline with dataclass record is a documented, proven pattern; build order and anti-patterns are grounded in real Python CLI practice |
| Pitfalls | HIGH (deliverability, secrets), MEDIUM (scraping brittleness, LLM consistency), LOW (Groq-specific quirks) | Deliverability and secrets risks are authoritative (Spamhaus, GitGuardian, official Resend docs); scraping and LLM consistency draw on community sources |

**Overall confidence:** HIGH

### Gaps to Address

- **Groq model availability:** The specific model name recommended (`llama-3.3-70b-versatile`) should be confirmed against the Groq console at implementation time; Groq's model catalog changes. Mitigation: make model name a config key so it can be swapped without code changes.
- **Email discovery hit rate:** The research is clear on the scraping approach, but real-world hit rates on a diverse company URL list are unknown until first dry-run. Mitigation: log HTTP status and page size from the start so hit rate can be audited; accept that some companies will be `no_email`.
- **Resend free tier daily quota:** The exact daily send limit on Resend's free tier is not pinned in the research. Mitigation: handle `daily_quota_exceeded` gracefully with an early exit; check the Resend dashboard before running large batches.

## Sources

### Primary (HIGH confidence)
- [typer · PyPI](https://pypi.org/project/typer/) — version 0.24.1, Python >=3.10
- [httpx · PyPI](https://pypi.org/project/httpx/) — version 0.28.1, sync+async, HTTP/2
- [beautifulsoup4 · PyPI](https://pypi.org/project/beautifulsoup4/) — version 4.14.3
- [lxml · PyPI](https://pypi.org/project/lxml/) — version 6.0.2
- [groq · PyPI](https://pypi.org/project/groq/) — version 1.1.1, Python >=3.10
- [resend · PyPI](https://pypi.org/project/resend/) — version 2.23.0
- [tenacity · PyPI](https://pypi.org/project/tenacity/) — version 9.1.4
- [tomllib — Python 3 docs](https://docs.python.org/3/library/tomllib.html) — stdlib since 3.11, read-only
- [Resend API Rate Limit documentation](https://resend.com/docs/api-reference/rate-limit) — 2 req/s default, error objects not exceptions
- [Spamhaus: Cold Emailing](https://www.spamhaus.org/resource-hub/spam/spamhaus-take-on-cold-emailing-aka-spam/) — authoritative anti-spam guidance
- [Python Secrets Management — GitGuardian](https://blog.gitguardian.com/how-to-handle-secrets-in-python/) — env var separation best practices
- [Typer official site](https://typer.tiangolo.com/) — CLI framework patterns
- [httpx official site](https://www.python-httpx.org/) — HTTP/2, sync+async API
- [Start Data Engineering: Idempotent Pipelines](https://www.startdataengineering.com/post/why-how-idempotent-data-pipeline/) — append-only log as state store pattern

### Secondary (MEDIUM confidence)
- [Cold Email Deliverability Best Practices 2025 — SuperSend](https://supersend.io/blog/cold-email-deliverability-best-practices-2025) — safe send limits (~50/day per inbox)
- [Safe Sending Limits — Topo.io](https://www.topo.io/blog/safe-sending-limits-cold-email) — max 100/day per address
- [How to Scrape Emails — Apify blog](https://blog.apify.com/scrape-emails-from-websites/) — mailto + regex, footer/contact/about targets
- [Web Scraping Emails — ScrapingBee](https://www.scrapingbee.com/blog/how-to-scrape-emails-from-any-website-for-sales-prospecting/) — requests + BeautifulSoup pattern confirmation
- [Hunter.io AI Cold Email Guide 2025](https://hunter.io/ai-cold-email-guide) — AI email pitfalls: generic outputs, formal tone, placeholder leakage
- [Avoid Bot Detection — Crawlshift](https://www.crawlshift.dev/blog/avoid-bot-detection-python-web-scraping) — User-Agent and scraping bot detection
- [Cold Email Domain Health — Mailforge](https://www.mailforge.ai/blog/cold-email-domain-health-best-practices-for-scaling) — subdomain strategy for outreach
- [Simon Willison: CLI Tools in Python](https://simonwillison.net/2023/Sep/30/cli-tools-python/) — CLI architecture patterns
- [Start Data Engineering: Pipeline Patterns](https://www.startdataengineering.com/post/code-patterns/) — continue-on-error pattern

---
*Research completed: 2026-03-14*
*Ready for roadmap: yes*
