# Feature Research

**Domain:** Cold email outreach CLI — developer job search automation
**Researched:** 2026-03-14
**Confidence:** HIGH (project requirements are explicit; domain patterns are well-established)

## Feature Landscape

### Table Stakes (Users Expect These)

Features the tool must have to be usable at all. Missing any of these makes the tool broken for its core purpose.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| CSV input of company URLs | Core input contract — the whole pipeline starts here | LOW | Single-column CSV; no preprocessing; strip whitespace, skip blank rows |
| Email address discovery from homepage | The primary "find a contact" mechanism | MEDIUM | Scan footer HTML for `mailto:` links + regex; fall through to /contact then /about |
| Company name inference from domain | Required for personalized message generation | LOW | Strip TLD, capitalize: `stripe.com` → "Stripe"; edge cases (e.g. `acme-corp.io`) need basic slug handling |
| LLM-generated personalized intro | Core differentiator vs manual emailing — the reason the tool exists | MEDIUM | Groq API; structured prompt with developer profile + inferred company/industry; enforce 60–180 word output via prompt constraint |
| Send email via Resend API | Delivery mechanism | LOW | Single API call per record; handle error objects (Resend does not throw exceptions on rate-limit errors) |
| Per-company logging (CSV or JSONL) | Without this, user has no record of what was sent to whom | MEDIUM | Fields: url, company_name, email_found, generated_message, status, resend_message_id, timestamp |
| `--dry-run` flag | Safety contract — scrape and generate but do not send | LOW | Must be explicit in CLI help; default should NOT send accidentally |
| Configurable delay between sends | Spam signal prevention; required for deliverability | LOW | Config key, default to ~10–30s; Resend default rate limit is 2 req/s but safe send cadence is much slower |
| Developer profile config file (`profile.toml`) | Write once, reuse across all runs | LOW | name, stack, years_experience, target_role, links; read at runtime, validate presence of required keys |

### Differentiators (Competitive Advantage)

Features that separate this tool from a generic "send emails from CSV" script. Focused on quality of output and operational safety.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Ordered fallback scrape strategy (footer → /contact → /about) | Finds more emails without fragile crawling; stops at first success to minimize requests | MEDIUM | Implement as a short priority list; log which page yielded the email for debugging |
| LLM-enforced word count + no-cliché prompt constraints | Prevents AI "boilerplate stink" — AI emails that feel generic destroy response rates | LOW | System prompt: "60–180 words, no phrases like 'I hope this finds you well', no placeholders, company-specific" |
| Industry inference via LLM from domain name | Avoids extra HTTP requests; good enough for personalization signals | LOW | Pass domain as context; LLM infers "payments infrastructure", "developer tools", etc. |
| `no_email_found` status logging | Surfaces which companies had no discoverable email — actionable signal | LOW | Log row with status=no_email_found; user can manually follow up or skip |
| Idempotent run guard (skip already-sent) | Prevents accidental double-send if run is interrupted and restarted | MEDIUM | Check log file for matching URL + status=sent before processing; requires deterministic log format |
| Preview output before sending | Lets user review LLM-generated messages before committing to a send batch | MEDIUM | `--preview` flag prints table of company → email → message without sending; pairs with dry-run |
| Message approval gate | User confirms each message before send in interactive mode | HIGH | Optional interactive prompt; useful for first run to calibrate prompt quality; can be skipped with `--no-confirm` |
| Configurable LLM model selection | Different Groq models have different speed/quality tradeoffs | LOW | Config key `groq_model`; default to `llama-3.3-70b-versatile` or equivalent; easy to swap |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem useful but add scope without proportionate value at v1 — or introduce real harm.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| LinkedIn / social scraping for email discovery | More email coverage | Fragile (rate limits, login walls, ToS violations, frequent breakage); disproportionate complexity for personal tool | Stick to public HTML pages; user manually adds LinkedIn emails to CSV if needed |
| Reply tracking / open tracking | Know who responded | Requires tracking pixels (often flagged as spam), webhook infrastructure, external service; turns personal tool into a mini-CRM | User checks their inbox; this is a personal tool, not a SaaS |
| Follow-up sequence scheduling | Automate follow-ups | Requires persistent state, scheduler, deduplication logic; significant complexity for v1 | Manual: user re-runs tool with a filtered CSV of non-responders |
| Email verification (bounce prediction) | Reduce bounce rate | Third-party API costs, adds latency, imperfect; acceptable bounce rate achievable with careful scraping | Use scraped emails only from explicit `mailto:` links, not guessed patterns |
| Web UI or dashboard | Easier to use | Overkill for personal tool; adds auth, serving, JS build step; out of scope per PROJECT.md | CLI is the right interface for this user |
| Multi-user / team support | Share with colleagues | Requires auth, per-user profiles, isolation; fundamentally changes architecture | This is a single-developer personal tool |
| Email guessing (name@domain pattern matching) | More email coverage | High bounce rate; ISPs treat bounces above 2% as spam signal; damages domain reputation | Only use discovered emails from public HTML |
| Automatic domain warmup | Better deliverability | Complex infrastructure; irrelevant for a personal tool sending <50 emails/day | Keep sends under 50/day; use a sending domain separate from primary domain |
| SMTP fallback | Independence from Resend | Adds configuration complexity; Resend is reliable and developer-friendly; SMTP adds auth/port troubleshooting | Hard dependency on Resend is fine per project constraints |

## Feature Dependencies

```
[CSV Input]
    └──required-by──> [Email Discovery]
                          └──required-by──> [LLM Generation]
                                                └──required-by──> [Send via Resend]
                                                                      └──required-by──> [Per-company Logging]

[Developer Profile Config]
    └──required-by──> [LLM Generation]

[--dry-run flag]
    └──gates──> [Send via Resend]
    └──does-not-gate──> [Email Discovery]
    └──does-not-gate──> [LLM Generation]
    └──does-not-gate──> [Per-company Logging]  (log even in dry-run with status=dry_run)

[Configurable Delay]
    └──wraps──> [Send via Resend]

[Idempotent Run Guard]
    └──reads──> [Per-company Logging]
    └──gates──> [Email Discovery] (skip already-processed URLs)

[Preview / --preview flag]
    └──requires──> [LLM Generation]
    └──conflicts-with──> [Send via Resend] (preview mode does not send)

[Message Approval Gate]
    └──requires──> [LLM Generation]
    └──gates──> [Send via Resend]
```

### Dependency Notes

- **Send via Resend requires Email Discovery:** You cannot send without a found address. If no email is discovered, the row is logged as `no_email_found` and skipped — no LLM call is made (saves API cost).
- **LLM Generation requires Developer Profile Config:** The prompt must be grounded in the user's actual profile. Missing config keys should fail fast with a clear error, not produce generic output.
- **Per-company Logging must capture dry-run runs:** Log with `status=dry_run` so idempotent guard still works correctly on subsequent real runs.
- **Idempotent guard reads the log:** This creates a soft ordering constraint: log file format must be stable before implementing idempotency. Get logging right first.
- **Preview conflicts with Send:** These are mutually exclusive modes; `--preview` prints, `--dry-run` does everything except send, a live run sends. Three distinct execution modes.

## MVP Definition

### Launch With (v1)

Minimum viable product — what is needed to validate the core workflow end-to-end.

- [ ] CSV input parsing — reads single-column URLs, skips blanks
- [ ] Email discovery: footer → /contact → /about fallback chain; regex + mailto extraction
- [ ] Company name inference from domain
- [ ] Developer profile loaded from `profile.toml`
- [ ] Groq LLM message generation with word count + no-cliché constraints
- [ ] Send via Resend API with basic error handling
- [ ] Per-company CSV log with all required fields
- [ ] `--dry-run` flag that skips send but logs with `status=dry_run`
- [ ] Configurable send delay (config key + sane default)

### Add After Validation (v1.x)

Features to add once the core pipeline is working and quality is confirmed.

- [ ] Idempotent run guard (skip already-sent URLs) — add when first interrupted run occurs
- [ ] `--preview` flag to print message table before committing — add when prompt tuning is needed
- [ ] Configurable LLM model selection — add when speed/quality tradeoff becomes relevant
- [ ] `no_email_found` filtering / reporting summary at end of run — add for operational convenience

### Future Consideration (v2+)

Features to defer until core workflow is validated and daily use patterns are understood.

- [ ] Message approval gate (`--confirm` interactive mode) — useful but adds friction; defer until prompt quality is trusted
- [ ] Follow-up batch generation (re-run on non-responders subset) — requires user workflow understanding
- [ ] Multiple output formats (JSONL, SQLite) — defer until CSV proves insufficient

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| CSV input + URL parsing | HIGH | LOW | P1 |
| Email discovery (3-page fallback) | HIGH | MEDIUM | P1 |
| Developer profile config | HIGH | LOW | P1 |
| LLM message generation | HIGH | MEDIUM | P1 |
| Send via Resend | HIGH | LOW | P1 |
| Per-company CSV logging | HIGH | LOW | P1 |
| `--dry-run` flag | HIGH | LOW | P1 |
| Configurable send delay | HIGH | LOW | P1 |
| `no_email_found` status + skip logic | MEDIUM | LOW | P2 |
| `--preview` output mode | MEDIUM | LOW | P2 |
| Idempotent run guard | MEDIUM | MEDIUM | P2 |
| Configurable LLM model | LOW | LOW | P2 |
| Message approval gate | MEDIUM | HIGH | P3 |
| Run summary / stats output | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

Note: This is a personal CLI tool, not a commercial product. "Competitors" here means comparable developer-built outreach tools and commercial SaaS features — used to inform what patterns are standard vs novel.

| Feature | Commercial tools (Instantly, Saleshandy, Lemlist) | Generic Python email scripts | Our approach |
|---------|--------------------------------------------------|------------------------------|--------------|
| Email discovery | Hunter.io API, LinkedIn scraping, purchased lists | Often none — user provides email list | Public HTML scraping only (footer/contact/about); no third-party APIs |
| Personalization | Template variables + AI icebreakers | String interpolation | Full LLM generation with company + developer context; no templates |
| Send safety | Domain warming, rotation, per-inbox limits | None | Configurable delay; `--dry-run`; daily volume naturally low (personal tool) |
| Logging | Full campaign analytics dashboard | Print statements | Structured CSV log per run; all fields preserved for manual review |
| Config | UI-based | Hardcoded | `profile.toml` + config file; git-safe (no secrets in code) |
| Follow-ups | Multi-step sequences | Not supported | Out of scope v1; manual re-run workflow |
| Email verification | Built-in verify step | Not present | Not in v1; rely on scraping quality |

## Sources

- [Resend API Rate Limits](https://resend.com/docs/api-reference/rate-limit) — official; rate limit is 2 req/s default, plan-based email quotas
- [Cold Email Deliverability Best Practices 2025 — SuperSend](https://supersend.io/blog/cold-email-deliverability-best-practices-2025) — safe send limit ~50/day per inbox for cold outreach
- [Cold Email Sending Limits 2025 — Topo.io](https://www.topo.io/blog/safe-sending-limits-cold-email) — max 100/day per sending address; stay under 50 for safety
- [How to scrape emails from a website — Apify blog](https://blog.apify.com/scrape-emails-from-websites/) — mailto link + regex patterns; footer/contact/about as primary targets
- [ScrapingBee: How to scrape emails with Python](https://www.scrapingbee.com/blog/how-to-scrape-emails-from-any-website-for-sales-prospecting/) — requests + BeautifulSoup patterns; confirms mailto: + regex as standard approach
- [Hunter.io AI Cold Email Guide 2025](https://hunter.io/ai-cold-email-guide) — AI email pitfalls: generic outputs, formal tone, placeholder leakage
- [Groq Prompt Engineering Patterns](https://console.groq.com/docs/prompting/patterns) — structured prompts with roles, context, format constraints
- [Leveraging Python for Cold Email Outreach — DEV Community](https://dev.to/rikinptl/leveraging-python-for-efficient-cold-email-outreach-to-recruiters-a-practical-guide-3p25) — comparable personal tool pattern; CSV in, email out, logging
- [Future of Cold Email 2026–2027 — Instantly.ai](https://instantly.ai/blog/future-of-cold-email-ai-personalization-automation-trends-shaping-2026-2027/) — relevance + trust + specificity are the differentiating signals

---
*Feature research for: cold email outreach CLI — developer job search*
*Researched: 2026-03-14*
