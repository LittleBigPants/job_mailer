# Pitfalls Research

**Domain:** Python CLI cold email outreach tool (scraping + LLM generation + transactional email)
**Researched:** 2026-03-14
**Confidence:** HIGH (deliverability, secrets management), MEDIUM (scraping brittleness, LLM consistency), LOW (Groq-specific quirks)

---

## Critical Pitfalls

### Pitfall 1: Sending From Your Primary Domain Without Authentication

**What goes wrong:**
Cold outreach sent from the same domain you use for all other email gets flagged or bounced. If your sender reputation tanks, it takes legitimate email (replies from recruiters, GitHub notifications, etc.) down with it.

**Why it happens:**
Developers reach for the obvious Resend-verified domain (usually their own primary domain) because it's already set up. The consequence of reputation damage is non-obvious until it's too late.

**How to avoid:**
Use a separate subdomain for outreach (e.g., `outreach.yourdomain.com` or `jobs.yourdomain.com`). Authenticate it with SPF, DKIM, and DMARC records before sending a single email. Resend supports custom domains and will walk through DNS record setup. Never send cold volume from the same domain that receives important inbound email.

**Warning signs:**
- Resend dashboard shows growing bounce rate (>2%) or spam complaint rate (>0.1%)
- Test emails landing in spam for your own Gmail/Outlook account
- Recruiters' replies start bouncing back to you

**Phase to address:**
Infrastructure setup phase — DNS records and Resend domain configuration must happen before any send logic is written.

---

### Pitfall 2: Accidental Email Blast on First Real Run

**What goes wrong:**
The tool works fine on a 3-row test CSV. On first real run with 80 companies, all emails fire in a tight loop with no delay. Recipients receive duplicate sends (if the run crashes and restarts with no idempotency check). Your domain gets flagged for sudden high-volume activity.

**Why it happens:**
The happy path gets tested, not the "what if this runs twice" path. Idempotency is deferred as a "nice to have." Delays feel unnecessary during development.

**How to avoid:**
- Log every sent email immediately with a `status` field before the next iteration, not after the batch
- Use a persistent log file (JSON Lines / CSV) so a restart can skip already-sent entries by checking `resend_message_id` presence
- Require `--dry-run` to be explicitly opt-out, not opt-in — default behavior should prompt for confirmation when >N emails are queued
- Make `send_delay_seconds` required config with no zero-second default

**Warning signs:**
- Log file is written at the end of the run rather than per-email
- No deduplication check before sending
- Restart after crash re-processes the full CSV

**Phase to address:**
Email sending phase — idempotency logic and per-email logging must be designed before the send loop, not added afterward.

---

### Pitfall 3: LLM Output Contains Clichés, Placeholders, or Fabricated Facts

**What goes wrong:**
The LLM generates emails that sound robotic ("I hope this email finds you well"), include unfilled template slots ("[Company Name]"), or make up facts about the company ("I see you recently raised a Series B"). These get sent verbatim.

**Why it happens:**
LLMs are probabilistic and their output is never fully deterministic. Prompts that work for 90% of inputs will produce garbage for the remaining 10% — especially for short, unusual domain names where the model has no real signal about the company. Developers review a few sample outputs and assume consistency.

**How to avoid:**
- Add post-generation validation before sending: check for bracket patterns (`\[.*?\]`), word count bounds (60–180 words per spec), and a small deny-list of cliché openers ("I hope this", "I came across", "My name is")
- Log the full generated message in every record so failures are auditable
- Test prompts against 10+ diverse domains including obscure ones (single-word domains, non-English domains, very new companies) before using in production
- Set `temperature=0` or very low (0.2) for consistency; Groq supports this parameter
- Use `--dry-run` to review generated messages before committing to a send

**Warning signs:**
- Prompt contains phrases like "write a personalized email about [company]" without explicit anti-cliché instructions
- Generated output not validated for length or bracket presence before sending
- All test domains are well-known companies (Stripe, Shopify, etc.) — edge cases never tested

**Phase to address:**
LLM generation phase — prompt design and output validation must be treated as first-class engineering, not a one-liner API call.

---

### Pitfall 4: Scraper Breaks Silently on Protected or JavaScript-Heavy Pages

**What goes wrong:**
`requests` + `BeautifulSoup` only sees what the server returns in the initial HTTP response. Many contact pages load email addresses via JavaScript, behind a login wall, or in obfuscated form (e.g., `user [at] domain.com`, base64-encoded strings, or split strings concatenated in JS). The scraper returns `no_email_found` — silently — for every such page.

**Why it happens:**
It works on straightforward static sites, so it appears to work. The false negative rate (missed emails) is invisible unless logs are audited. The fallback chain (footer → /contact → /about) gives false confidence that all bases are covered.

**How to avoid:**
- Log the HTTP status code and whether content was returned for each page fetch — don't just log `no_email_found`
- Treat non-200 responses, empty bodies, and redirect-to-login as distinct failure modes, not "no email found"
- Obfuscation patterns to handle: `[at]`, `(at)`, `user AT domain DOT com`, HTML entity encoding (`&#64;` for `@`), and basic ROT13
- Set a realistic User-Agent string (not the default `python-requests/x.x.x`) to avoid trivial bot detection
- Accept the limit — don't try to handle Cloudflare-protected sites or JS-rendered pages; log them as `scrape_blocked`

**Warning signs:**
- Scraper runs on 30 URLs and finds emails on only 1-2 of them (suspiciously low hit rate)
- No differentiation in logs between "no email exists" and "scraper couldn't access page"
- HTML responses shorter than 1KB for well-known company pages (bot detection redirect)

**Phase to address:**
Scraping phase — failure taxonomy must be designed into the logging schema from the start. Add obfuscation normalization in the same phase.

---

### Pitfall 5: API Keys Committed to the Repository

**What goes wrong:**
`profile.toml` or a config file holds the Groq API key and Resend API key. The file is committed. Keys get exposed via GitHub, cloned repos, or CI logs. Groq and Resend keys can be used to run up API bills or send email as you.

**Why it happens:**
It's a personal tool, so security feels like overkill. The config and profile are in the same file, which the developer naturally wants to commit (profile data is not sensitive). The boundary between "profile config" and "secrets" is blurred.

**How to avoid:**
- Separate profile data (`profile.toml` — commit-safe, contains name/stack/links) from secrets (`.env` or environment variables — never committed)
- Load `GROQ_API_KEY` and `RESEND_API_KEY` exclusively from environment variables at runtime
- Add `.env` to `.gitignore` on day one, before the file exists
- Consider `python-dotenv` to load `.env` for local runs without requiring the user to `export` manually
- Never put keys in `profile.toml` even as placeholders — it normalizes the anti-pattern

**Warning signs:**
- `profile.toml` has any fields named `api_key`, `token`, or `secret`
- The README says "add your API key to config.toml"
- `.gitignore` doesn't exist or doesn't include `.env`

**Phase to address:**
Project scaffolding / initial setup phase — `.gitignore`, env var loading, and the profile/secrets split must be established before any API integration code is written.

---

### Pitfall 6: Resend 429 Errors Crash the Run Silently

**What goes wrong:**
Resend enforces a default rate limit of 2 requests per second and has daily/monthly quotas on the free tier. When the limit is hit, Resend returns a `429` error object — it does not raise an exception. Code that checks only for successful response without inspecting the error type will log a false "sent" status or crash without a useful message, leaving the rest of the batch unsent.

**Why it happens:**
Developers assume HTTP errors throw exceptions (like `requests.raise_for_status()`). Resend's Python SDK returns error objects instead of raising. The rate-limit scenario is never hit in small tests (< 2 emails/sec is easy to stay under), so the code path is never exercised.

**How to avoid:**
- Always inspect the Resend response for `error` field before logging success
- Handle `429` explicitly: log `status=rate_limited`, sleep for `retry-after` seconds, and retry once
- Keep `send_delay_seconds` at a value that naturally stays under 2 req/s (1+ second delay is sufficient)
- For free tier: check daily quota before starting a large batch, or handle `daily_quota_exceeded` gracefully with an early exit and clear error message

**Warning signs:**
- Send loop has no error type inspection on Resend response
- No retry logic anywhere in the send path
- `send_delay_seconds` defaults to 0 or is absent from config

**Phase to address:**
Email sending phase — Resend response handling must explicitly cover `429`, `daily_quota_exceeded`, and other error types from the first implementation.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Write log at end of run instead of per-email | Simpler code | Lost records if run crashes mid-batch; enables double-sends on restart | Never |
| Hardcode delay as a constant instead of config | Faster to write | Must modify source to tune; no way to slow down for a sensitive domain | Never |
| Single config file for profile + API keys | One file to manage | Keys get committed to version control | Never |
| Skip User-Agent header in requests | No extra code | Blocked immediately by any basic bot detection | Never for production use |
| Validate prompt output only manually during dev | Fast iteration | Clichés and placeholders reach real recipients | Only for first dry-run test; automate before first live send |
| No idempotency check on restart | Simpler loop | Duplicate sends to same contacts if run is interrupted | Never |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Resend API | Assuming exceptions are thrown on error | Check response object for `error` field; handle `429` and quota errors explicitly |
| Resend API | Sending from primary domain | Configure and authenticate a dedicated subdomain before first send |
| Resend free tier | Not checking daily quota | Handle `daily_quota_exceeded` with a graceful early exit and human-readable message |
| Groq API | Treating output as always well-formed | Validate word count, check for bracket placeholders, check for flagged clichés before sending |
| Groq API | Using high temperature for "creativity" | Use temperature ≤ 0.2 for consistency; creativity is not the goal, authentic-sounding brevity is |
| HTTP scraping | Default `python-requests` User-Agent | Set a realistic browser User-Agent string on every request |
| HTTP scraping | Treating non-200 as "no email found" | Log distinct status codes — 403/429/503 mean blocked, not absent |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| No delay between scrape requests to same domain | Consecutive scrapes of footer + /contact + /about trigger rate-limit or IP block | Add 0.5–1s delay between page fetches for the same domain | Immediately on domains with basic rate limiting |
| No delay between Groq API calls | Context window saturation or rate-limit errors if batch is large | Groq has per-minute token limits; validate and add small delay if batch > 50 | Around 50–100 rapid calls on free-tier Groq |
| Loading entire CSV into memory before starting | No issue at CSV of 100 rows | Not a real concern at personal tool scale | Never at this scale — not a real trap |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| API keys in `profile.toml` or any committed file | Keys exposed via git history, clones, or public repos; attacker sends email as you or runs up LLM bills | Load all keys from environment variables only; never from committed config files |
| Logging full email body to a file with no access controls | Generated emails (which contain your name, target companies, personal pitch) accumulate in a file readable by any process | Keep log file local, add to `.gitignore` if it contains anything sensitive, or at minimum document clearly |
| No confirmation prompt before live send | Accidental full-blast send while testing | Require explicit confirmation or `--confirm` flag when not in `--dry-run` mode and batch > N |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Silent `no_email_found` with no context | User can't tell if the URL was blocked, returned a bad page, or genuinely has no email | Log HTTP status, page size, and reason for no-email outcome separately |
| No progress indicator during a 40-company run | Run appears frozen for minutes; user kills it | Print one-line progress per company: URL being processed, outcome |
| `--dry-run` output only visible in logs, not stdout | User has to open log file to review generated messages | Print generated messages to stdout during dry-run in a readable format |
| Ambiguous error when `profile.toml` is missing or malformed | Stack trace instead of actionable message | Validate and fail fast with a clear message: "profile.toml not found at X — see README" |
| Run stops completely on first scrape error | One bad URL kills the batch | Catch per-company errors, log them, and continue to next URL |

---

## "Looks Done But Isn't" Checklist

- [ ] **Scraping:** Handles 3xx redirects (requests follows them by default, but logging should capture final URL) — verify redirect chains don't loop
- [ ] **Scraping:** Obfuscated email formats (`[at]`, `(at)`, HTML entities) are normalized before regex match — verify with a test URL that uses obfuscation
- [ ] **LLM output:** Bracket placeholder detection runs on every generated message — verify with a prompt that includes a domain the LLM knows nothing about
- [ ] **LLM output:** Word count is checked and logged — verify an edge case short domain produces output within 60–180 words
- [ ] **Email sending:** Resend response is inspected for error field, not just HTTP 200 — verify by mocking a 429 response
- [ ] **Idempotency:** Re-running the tool with the same CSV after a partial run skips already-sent entries — verify by interrupting a dry-run and restarting
- [ ] **Secrets:** `.env` is in `.gitignore` and `profile.toml` contains zero API keys — verify with `git status` after setup
- [ ] **Dry-run:** `--dry-run` produces output on stdout reviewable before any live send — verify that no Resend calls are made during dry-run

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| API keys committed to repo | HIGH | Rotate keys immediately in Groq and Resend dashboards; use `git filter-branch` or BFG to purge history; force-push (if private repo) or treat keys as permanently compromised |
| Domain reputation damaged by high bounce rate | HIGH | Stop all sends; check MX records for bad addresses; warm up sending volume slowly over 2–4 weeks; consider switching to a fresh subdomain |
| Duplicate emails sent to same contact | MEDIUM | Log review to determine scope; send one brief apology if relationship is important; no automated recovery path — manual only |
| Generated message with fabricated claim sent | MEDIUM | Cannot unsend; add post-generation validation to catch future occurrences; document what validation catches and what it misses |
| Groq quota exhausted mid-batch | LOW | Handle `429` with early exit; re-run with same CSV (idempotency skips already-sent entries); generated messages can be cached per-domain to avoid re-generating |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| API keys in committed files | Project scaffolding | `git status` shows no `.env`; `profile.toml` has no key fields; `.gitignore` present |
| Domain reputation / no DNS auth | Infrastructure setup | Resend dashboard shows domain as "Verified"; SPF/DKIM/DMARC records confirmed via MXToolbox |
| LLM clichés and placeholder leakage | LLM generation phase | Post-generation validation function tested against ≥10 diverse domains including obscure ones |
| Scraper silent failures | Scraping phase | Log schema includes HTTP status, page size, and failure reason distinct from `no_email_found` |
| Resend 429 / quota errors crashing run | Email sending phase | Error handling tested with mocked 429 response; retry logic present |
| Accidental blast / no idempotency | Email sending phase | Restart after mid-run crash skips already-logged entries; `--dry-run` tested before any live send |
| No per-email logging | Email sending phase | Each send writes one log entry immediately; crash mid-batch shows partial records, not empty log |

---

## Sources

- [Resend API Rate Limit documentation](https://resend.com/docs/api-reference/rate-limit) — official, HIGH confidence
- [5 Email Deliverability Mistakes Killing Your Cold Outreach — Apollo](https://www.apollo.io/magazine/5-email-deliverability-mistakes-killing-your-cold-outreach) — MEDIUM confidence
- [Cold Email Domain Health Best Practices — Mailforge](https://www.mailforge.ai/blog/cold-email-domain-health-best-practices-for-scaling) — MEDIUM confidence
- [Cold Email Deliverability Best Practices 2025 — SuperSend](https://supersend.io/blog/cold-email-deliverability-best-practices-2025) — MEDIUM confidence
- [How to Avoid Bot Detection in Python Web Scraping — Crawlshift](https://www.crawlshift.dev/blog/avoid-bot-detection-python-web-scraping) — MEDIUM confidence
- [Web Scraping Emails Using Python — Scrapfly](https://scrapfly.io/blog/posts/how-to-scrape-emails-using-python) — MEDIUM confidence
- [Spamhaus Take on Cold Emailing](https://www.spamhaus.org/resource-hub/spam/spamhaus-take-on-cold-emailing-aka-spam/) — HIGH confidence (authoritative anti-spam source)
- [Cold Email Compliance: GDPR, CAN-SPAM & AI-driven Outreach — Smartlead](https://www.smartlead.ai/blog/cold-email-compliance) — MEDIUM confidence
- [Python Secrets Management Best Practices — GitGuardian](https://blog.gitguardian.com/how-to-handle-secrets-in-python/) — HIGH confidence
- [Mastering Email Rate Limits — Resend API Deep Dive](https://dalenguyen.me/blog/2025-09-07-mastering-email-rate-limits-resend-api-cloud-run-debugging) — MEDIUM confidence

---
*Pitfalls research for: Python CLI cold email outreach tool (job_mailer)*
*Researched: 2026-03-14*
