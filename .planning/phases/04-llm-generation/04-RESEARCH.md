# Phase 4: LLM Generation - Research

**Researched:** 2026-03-14
**Domain:** Groq Python client, prompt engineering, LLM output validation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Developer info passed to LLM: key fields only — name, title, primary skills, specialisation, contact email (from profile.toml)
- Company signals: company_name + inferred industry + full URL
- Prompt structured with guardrails: explicit 60–180 word instruction, no cliché openers, no `[bracket]` placeholders, professional but warm tone, soft ask for role interest / brief chat
- On validation failure, retry prompt includes the failure reason explicitly (word count with exact N, bracket message, cliché message)
- One retry maximum; if retry also fails → `status=generation_failed`
- Terminal output on final failure: single WARNING line matching Phase 3 echo pattern
- `generate_email(record: CompanyRecord, profile: dict) -> CompanyRecord` — never raises on expected failures
- Returns record with `generated_message` populated and `status=PENDING` on success
- Returns record with `status=Status.GENERATION_FAILED` on double failure
- Cliché phrase matching: exact string match anywhere in the message body (not start-only)
- Model config key location: `profile.toml` under a `[generation]` section (e.g., `model = "llama-3.3-70b-versatile"`)
- Default model name when key absent: Claude's discretion (confirmed below — `llama-3.3-70b-versatile`)
- Exact prompt wording and system/user message split: Claude's discretion
- Word counting method: split on whitespace is sufficient
- Groq Python client setup: groq library (already in pyproject.toml)

### Claude's Discretion

- Default model fallback value
- Exact prompt wording and system/user split
- Word-count implementation (whitespace split confirmed)
- Groq client instantiation location (module-level vs per-call)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GEN-01 | Infer company name and industry from domain URL; pass both to LLM | `_infer_company_name()` already exists in scraper.py; industry inference is an LLM instruction in the prompt (no extra HTTP request needed) |
| GEN-02 | Groq LLM generates personalized email intro (60–180 words) using profile.toml | `groq>=1.1.1` already in dependencies; `client.chat.completions.create()` is the standard synchronous call; profile dict already loaded and validated before CSV loop |
| GEN-03 | Validate message: reject/retry once if outside word range, contains `[bracket]`, or matches cliché deny-list | Simple Python validators; retry appends failure reason to next prompt; deny-list is 5 fixed strings |
| GEN-04 | If validation fails after one retry, log as `generation_failed` and skip | `Status.GENERATION_FAILED` already in models.py; match `scrape_company()` no-exception interface |
</phase_requirements>

---

## Summary

Phase 4 adds a `generator.py` module with a single public function `generate_email(record, profile) -> CompanyRecord`. It calls the Groq chat completions API synchronously (matching the existing blocking pipeline), validates the response against three rules (word count, bracket placeholders, cliché openers), and retries once with the specific failure reason embedded in the follow-up prompt. The overall code volume is small — the Groq SDK usage is three lines, and all validation is string operations. The key risk is the LLM occasionally producing messages that fail validation even on retry; the design explicitly accepts this by returning `GENERATION_FAILED` rather than retrying indefinitely.

The `groq` library (>=1.1.1) is already declared as a project dependency. The `llama-3.3-70b-versatile` model is confirmed active on Groq's production platform as of 2026-03 with a 131,072-token context window, making it well-suited for this use case (prompt + response will be well under 2,000 tokens). No new dependencies are required for this phase.

**Primary recommendation:** Add `generator.py` as a new module. Keep Groq client instantiation local to the function call to avoid module-level side effects. Read the `[generation]` section from the profile dict for the model name; fall back to `"llama-3.3-70b-versatile"` when absent.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| groq | >=1.1.1 | Groq API Python SDK | Already in pyproject.toml; official Groq client; mirrors openai SDK interface |
| tomllib (stdlib) | 3.11+ | Read `[generation]` section from profile dict | Already used in config.py; no extra dependency needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| os (stdlib) | any | Read `GROQ_API_KEY` from environment | Used for `Groq(api_key=os.environ.get("GROQ_API_KEY"))` |
| re (stdlib) | any | Bracket placeholder detection | `re.search(r'\[.+?\]', message)` is clearer than manual string scanning |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| groq SDK | httpx direct call | SDK adds retry logic, type safety, and mirrors the openai interface — no reason to bypass it |
| groq SDK | LangChain ChatGroq | LangChain adds heavyweight dependency for no gain in this simple single-call scenario |

**Installation:**

No new installation required — `groq>=1.1.1` is already in `pyproject.toml` dependencies.

---

## Architecture Patterns

### Recommended Project Structure

```
src/job_mailer/
├── __main__.py     # CLI entry point — add generate_email call after scrape succeeds
├── config.py       # existing — no changes needed
├── models.py       # existing — no changes needed
├── scraper.py      # existing — no changes needed
└── generator.py    # NEW: generate_email() public function + private helpers
tests/
├── conftest.py     # existing — no changes needed
└── test_generator.py   # NEW: unit tests mocking Groq client
```

### Pattern 1: Groq Synchronous Chat Completion

**What:** Instantiate `Groq` client with `GROQ_API_KEY` from environment, call `client.chat.completions.create()`, read `choices[0].message.content`.
**When to use:** All production generation calls in this phase.

```python
# Source: https://console.groq.com/docs/text-chat (verified 2026-03-14)
import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
response = client.chat.completions.create(
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    model=model_name,
)
message_text = response.choices[0].message.content
```

### Pattern 2: Model Name from profile.toml `[generation]` section

**What:** Read `profile["generation"]["model"]` with a `.get()` fallback.
**When to use:** Every call to the generator, before constructing the Groq client.

```python
# profile.toml [generation] section; falls back to default if section absent
model_name = profile.get("generation", {}).get("model", "llama-3.3-70b-versatile")
```

### Pattern 3: Retry with Embedded Failure Reason

**What:** On first validation failure, build a second prompt that includes the exact failure message as a new user turn appended to the conversation history.
**When to use:** Any validation failure on the first attempt.

```python
# Build failure reason message
if word_count_outside_range:
    reason = f"The previous message was {word_count} words. Target: 60-180."
elif has_brackets:
    reason = "The previous message contained [bracket] placeholders. Remove them."
else:
    reason = "The previous message started with a cliche opener. Avoid those."

# Append to messages for retry
messages.append({"role": "assistant", "content": first_attempt})
messages.append({"role": "user", "content": reason})
response = client.chat.completions.create(messages=messages, model=model_name)
```

### Pattern 4: No-Exception Interface (matching scrape_company)

**What:** Catch all Groq SDK exceptions inside `generate_email()` and return `GENERATION_FAILED` rather than propagating.
**When to use:** Any `groq.APIConnectionError`, `groq.RateLimitError`, or `groq.APIStatusError`.

```python
# Source: https://github.com/groq/groq-python (error hierarchy, verified 2026-03-14)
try:
    response = client.chat.completions.create(...)
except groq.GroqError as exc:
    typer.echo(f"WARNING: generation_failed for {record.url} ({exc})", err=True)
    record.status = Status.GENERATION_FAILED
    return record
```

### Pattern 5: Industry Inference via Prompt Instruction

**What:** `_infer_company_name()` in scraper.py already extracts the domain slug. Industry inference is delegated to the LLM — the URL is passed as context and the LLM is instructed to infer the industry. No separate HTTP request needed (per STATE.md decision: "Industry inferred from domain slug only").
**When to use:** Always — pass `url` and `company_name` to LLM prompt, instruct it to infer industry from URL.

### Anti-Patterns to Avoid

- **Module-level Groq client:** Instantiating `client = Groq()` at module top-level makes testing harder and runs at import time. Instantiate inside `generate_email()`.
- **Raising exceptions for expected failures:** `scrape_company()` never raises on expected failures; `generate_email()` must match this contract exactly. `__main__.py` does not expect try/except.
- **Retrying more than once:** The spec allows exactly one retry. A loop with `range(2)` is tempting but risks drift — use an explicit first-attempt / retry structure instead.
- **Overly broad cliché match at line start only:** CONTEXT.md specifies "exact string match anywhere in the message body" — do not anchor to beginning of string.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retries on transient failures | Custom retry loop | groq SDK built-in (retries 2x on 429, 5xx, connection errors) | SDK handles exponential backoff automatically |
| TOML parsing | Custom parser | tomllib (stdlib, Python 3.11+) | Already used in config.py |

**Key insight:** This phase has very little "library problem" surface. The Groq SDK makes the API call; all other logic (word count, bracket check, cliché check) is plain string operations. Keep it simple.

---

## Common Pitfalls

### Pitfall 1: Groq Client Constructed Before GROQ_API_KEY is Set

**What goes wrong:** `Groq()` reads `GROQ_API_KEY` at construction time. If constructed at module level, tests that set the key via `monkeypatch` may not work — the client was already constructed without the key.
**Why it happens:** Module-level initialization runs at import time, before test fixtures run.
**How to avoid:** Instantiate `Groq(api_key=os.environ.get("GROQ_API_KEY"))` inside `generate_email()` (or a private helper it calls), so it runs after env setup.
**Warning signs:** Tests fail with `AuthenticationError` even though the key is in `monkeypatch`.

### Pitfall 2: Token Budget Underestimated

**What goes wrong:** A large prompt (profile + company data + system instructions) combined with a 180-word response could bump against the model's `max_completion_tokens` parameter.
**Why it happens:** The llama-3.3-70b-versatile model supports up to 32,768 completion tokens (context window 131,072), so this is unlikely in practice for this small use case, but leaving `max_completion_tokens` unset means the SDK default applies.
**How to avoid:** Set `max_completion_tokens=300` explicitly — generous for a 180-word max response, prevents runaway generation.
**Warning signs:** Generated message is truncated mid-sentence and word count is at the lower boundary unexpectedly.

### Pitfall 3: Word Count Method Inconsistency

**What goes wrong:** Using `len(message.split())` to count words but the LLM uses a different tokenization — leading to edge-case mismatch.
**Why it happens:** Different tools count "hyphenated-words" or URLs differently.
**How to avoid:** CONTEXT.md explicitly approves whitespace split: `len(message.split())`. Use it consistently in both validation and in the failure reason message embedded in the retry prompt.
**Warning signs:** Retry prompt says "210 words" but actual split count is 195.

### Pitfall 4: Cliché Match Case Sensitivity

**What goes wrong:** Cliché deny-list check misses "I Hope This Finds You" (title case from LLM).
**Why it happens:** String contains-check is case-sensitive by default.
**How to avoid:** Lowercase the message before checking: `message.lower()` for the deny-list match. Keep the original message for returning as `generated_message`.
**Warning signs:** CI passes but manual testing with a capitalised opener slips through.

### Pitfall 5: profile.toml `[generation]` Section Missing in Tests

**What goes wrong:** Tests pass a minimal profile dict without a `[generation]` key, causing a `KeyError` in `profile["generation"]["model"]`.
**Why it happens:** Defensive access not used.
**How to avoid:** Use `profile.get("generation", {}).get("model", "llama-3.3-70b-versatile")` — safe on absent section.

---

## Code Examples

Verified patterns from official sources:

### Groq Client — Sync Chat Completion

```python
# Source: https://console.groq.com/docs/text-chat (verified 2026-03-14)
from groq import Groq

client = Groq()  # reads GROQ_API_KEY from environment automatically
response = client.chat.completions.create(
    messages=[
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."},
    ],
    model="llama-3.3-70b-versatile",
    max_completion_tokens=300,
)
text = response.choices[0].message.content
```

### Groq Error Hierarchy

```python
# Source: https://github.com/groq/groq-python (verified 2026-03-14)
import groq

try:
    ...
except groq.APIConnectionError:
    ...  # network-level failure
except groq.RateLimitError:
    ...  # 429
except groq.APIStatusError as e:
    ...  # other HTTP error; e.status_code, e.response available
```

### Mocking Groq in pytest (unittest.mock approach)

```python
# Standard approach for mocking openai-compatible clients
from unittest.mock import MagicMock, patch

def test_generate_email_success(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Hello, I am a developer..."

    with patch("job_mailer.generator.Groq") as mock_groq_cls:
        mock_groq_cls.return_value.chat.completions.create.return_value = mock_response
        record = generate_email(record, profile)

    assert record.generated_message == "Hello, I am a developer..."
```

### Validation Helpers (all plain Python)

```python
import re

CLICHE_DENY_LIST = [
    "i hope this finds you",
    "quick question",
    "synergy",
    "touch base",
    "circle back",
]

def _word_count(text: str) -> int:
    return len(text.split())

def _has_brackets(text: str) -> bool:
    return bool(re.search(r'\[.+?\]', text))

def _has_cliche(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in CLICHE_DENY_LIST)
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, no version pinned in dev deps) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]`, `addopts = "-x"` |
| Quick run command | `uv run pytest tests/test_generator.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GEN-01 | LLM prompt includes company_name, inferred industry (via URL), and full URL | unit | `uv run pytest tests/test_generator.py::test_prompt_includes_company_signals -x` | Wave 0 |
| GEN-02 | Successful generation returns record with generated_message and status=PENDING | unit | `uv run pytest tests/test_generator.py::test_generate_email_success -x` | Wave 0 |
| GEN-03a | Message with [bracket] placeholder is rejected and retried with embedded reason | unit | `uv run pytest tests/test_generator.py::test_retry_on_brackets -x` | Wave 0 |
| GEN-03b | Message outside 60–180 words is rejected and retried with word count in reason | unit | `uv run pytest tests/test_generator.py::test_retry_on_word_count -x` | Wave 0 |
| GEN-03c | Message containing cliché phrase is rejected and retried | unit | `uv run pytest tests/test_generator.py::test_retry_on_cliche -x` | Wave 0 |
| GEN-04 | Double validation failure returns GENERATION_FAILED, no exception raised | unit | `uv run pytest tests/test_generator.py::test_double_failure_returns_generation_failed -x` | Wave 0 |
| GEN-04 | Model name driven by profile[generation][model] config key | unit | `uv run pytest tests/test_generator.py::test_model_name_from_config -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_generator.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_generator.py` — covers GEN-01, GEN-02, GEN-03, GEN-04 (all test stubs needed before production code)
- [ ] `profile.toml` `[generation]` section — add `model = "llama-3.3-70b-versatile"` to `profile.example.toml`

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `max_tokens` parameter | `max_completion_tokens` | Groq API aligned with OpenAI v1 | Old name deprecated; use `max_completion_tokens` |
| `httpx` direct REST calls | `groq` SDK | groq 0.x | SDK adds type safety, retry, error hierarchy |

**Deprecated/outdated:**

- `max_tokens` in Groq's API: replaced by `max_completion_tokens`. The SDK accepts both but `max_completion_tokens` is current.

---

## Open Questions

1. **Model name confirmed at implementation time**
   - What we know: `llama-3.3-70b-versatile` is active on Groq production as of 2026-03. Model catalog can change.
   - What's unclear: Whether a newer model (e.g., Llama 4 Scout) offers meaningfully better output quality for this use case.
   - Recommendation: Default to `llama-3.3-70b-versatile` in code. The `[generation]` config key makes it trivially swappable without code changes.

2. **System vs user message split for retry**
   - What we know: The retry appends failure reason as a new user turn. The Groq docs confirm multi-turn conversations are supported by including assistant + user turns in the messages array.
   - What's unclear: Whether keeping the original system prompt in the retry messages list is necessary (it almost certainly is).
   - Recommendation: Retry messages list = original system message + original user message + assistant's first response + new user message with failure reason. This is standard multi-turn chat pattern.

---

## Sources

### Primary (HIGH confidence)

- [console.groq.com/docs/text-chat](https://console.groq.com/docs/text-chat) — synchronous chat completions API, message structure, parameters
- [console.groq.com/docs/models](https://console.groq.com/docs/models) — llama-3.3-70b-versatile confirmed active in production, 131,072 context window, 32,768 max completion tokens
- [github.com/groq/groq-python](https://github.com/groq/groq-python) — error class hierarchy: APIConnectionError, RateLimitError, APIStatusError
- Existing codebase — models.py, config.py, scraper.py, __main__.py, pyproject.toml

### Secondary (MEDIUM confidence)

- [PyPI groq 1.1.1](https://pypi.org/project/groq/) — version confirmed in pyproject.toml; SDK auto-retries on 429/5xx
- [console.groq.com/docs/deprecations](https://console.groq.com/docs/deprecations) — `max_tokens` → `max_completion_tokens` deprecation

### Tertiary (LOW confidence)

- WebSearch results on pytest mocking patterns for openai-compatible clients — standard `unittest.mock.patch` approach; cross-verified with pytest-mock docs

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — groq library already in pyproject.toml; API confirmed current
- Architecture: HIGH — mirrors existing scraper.py patterns precisely; Groq SDK interface verified against official docs
- Pitfalls: HIGH — derived from existing codebase patterns and verified Groq SDK behavior
- Validation architecture: HIGH — existing pytest infrastructure; test stubs follow test_scraper.py pattern

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (model catalog changes within 30 days are possible but the config key mitigates this)
