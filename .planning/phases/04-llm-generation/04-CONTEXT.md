# Phase 4: LLM Generation - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Given a scraped `CompanyRecord` (with `company_name`, `email_found`, `url`) and a loaded developer profile, call the Groq LLM to generate a personalized email intro that passes post-generation validation — or return the record with `status=generation_failed` if both attempts fail. Sending and logging are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Prompt content
- Developer info passed to LLM: key fields only — name, title, primary skills, specialisation, contact email (from profile.toml)
- Company signals: company_name + inferred industry + full URL (URL gives LLM extra hints about product/stack)
- Prompt is structured with guardrails: explicit instructions for 60–180 words, no cliché openers, no `[bracket]` placeholders, professional but warm tone
- Purpose framing: include a soft ask — expressing interest in roles or requesting a brief chat (not intro-only)

### Retry behavior
- On validation failure, the retry prompt includes the failure reason explicitly:
  - Word count: `"The previous message was {N} words. Target: 60–180."`
  - Brackets: `"The previous message contained [bracket] placeholders. Remove them."`
  - Cliché: `"The previous message started with a cliché opener. Avoid those."`
- One retry maximum (per GEN-03/GEN-04); if retry also fails → `status=generation_failed`
- Terminal output on final failure: single warning line matching Phase 3 echo pattern, e.g.:
  `WARNING: generation_failed for stripe.com (cliché opener after retry)`

### Module interface
- `generate_email(record: CompanyRecord, profile: dict) -> CompanyRecord`
- Returns the record with `generated_message` populated and `status=PENDING` on success
- Returns the record with `status=Status.GENERATION_FAILED` on double failure — no exception raised
- Consistent with `scrape_company()` interface: caller doesn't need try/except for expected failures

### Claude's Discretion
- Cliché phrase matching: exact string match anywhere in the message body (not start-only)
- Model config key location: `profile.toml` under a `[generation]` section (e.g., `model = "llama-3.3-70b-versatile"`)
- Default model name to use when key is absent: Claude's discretion (STATE.md notes `llama-3.3-70b-versatile` as candidate; confirm against Groq console at implementation time)
- Exact prompt wording and system/user message split
- Word counting method (split on whitespace is sufficient)
- Groq Python client setup (groq library or httpx direct call)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CompanyRecord` (models.py): `url`, `company_name`, `generated_message`, `status` fields are all present — generator populates `generated_message` and updates `status`
- `Status.GENERATION_FAILED` (models.py): already defined — no enum changes needed
- `load_profile()` (config.py): returns the full profile dict; generator receives this dict directly
- `scrape_company()` (scraper.py): returns `CompanyRecord` without raising on expected failures — generator should match this interface

### Established Patterns
- Synchronous pipeline throughout — no async; Groq API call is a blocking HTTP call
- `sys.exit()` for fatal config errors; per-row failures use `typer.echo(err=True)` (not sys.exit)
- Functions return populated dataclass instances; `__main__.py` handles per-row orchestration

### Integration Points
- `__main__.py` currently calls `scrape_company(url)` and echoes status — Phase 4 adds `generate_email(record, profile)` call after scrape succeeds
- `profile` dict already loaded and validated in `main()` before the CSV loop — passes cleanly to `generate_email()`

</code_context>

<specifics>
## Specific Ideas

- Retry prompt must include exact word count, not just direction: `"The previous message was 210 words. Target: 60–180."`
- STATE.md flags that the Groq model name must be confirmed against Groq console at implementation time — `llama-3.3-70b-versatile` is the current candidate

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-llm-generation*
*Context gathered: 2026-03-14*
