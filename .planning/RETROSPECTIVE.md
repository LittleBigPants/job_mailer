# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-03-15
**Phases:** 6 | **Plans:** 18 | **Timeline:** 2 days (2026-03-14 → 2026-03-15)

### What Was Built
- Python CLI tool (`job-mailer`) built on Typer, httpx, BeautifulSoup, Groq SDK, Resend SDK
- Multi-page email scraper: homepage → /contact → /about fallback chain with company name inference
- Groq LLM generation: 60–180 word personalized intros, cliché deny-list, one-retry validation
- Resend email delivery with named error inspection (429, quota, invalid_email) and configurable delay
- Append-only CSV log: immediate per-row writes, all 7 fields captured
- Full CLI orchestration: --dry-run, --delay, idempotent re-runs (skip status=sent), within-run dedup
- 49 tests passing at ship

### What Worked
- **Strict dependency ordering** — building phases in pipeline order (infra → model → scraper → generator → sender → orchestrator) meant each phase had everything it needed; no backtracking
- **TDD RED/GREEN commits** — failing test commit followed by implementation commit made regressions impossible and gave instant confidence on phase completion
- **Status enum as shared contract** — defining all named outcomes (sent, rate_limited, no_email_found, generation_failed, dry_run) upfront in models.py kept every phase's logging consistent without coordination overhead
- **Audit before completion** — running `/gsd:audit-milestone` surfaced the Phase 4 roadmap discrepancy and five minor tech-debt items that were resolved cleanly before archival

### What Was Inefficient
- **Phase 4 roadmap status not updated** — roadmap showed Phase 4 as "In Progress" even after completion; required manual fix at archive time. Should update ROADMAP.md as part of phase completion
- **VALIDATION.md templates unfilled** — Nyquist compliance files were planning scaffolds that never got populated; tests exist and pass, but the formal validation records are empty. This is cosmetic tech debt
- **SUMMARY.md frontmatter non-standard** — plans used `dependency/tech-stack` schema instead of the expected `requirements_completed` field; summary-extract couldn't auto-pull accomplishments

### Patterns Established
- `load_dotenv()` at module top-level (never inside a function) — prevents env var race conditions when multiple modules read os.environ
- `conftest.py` autouse fixture to clear env vars between tests — required whenever module-level `load_dotenv()` is present
- `sys.exit()` for config validation errors (not `raise`) — human-readable messages instead of tracebacks
- Append-only CSV log with immediate per-row writes — crash-safe; enables idempotent re-runs
- `.gitignore` committed before any file it ignores — prevents accidental secret staging

### Key Lessons
1. **Name every outcome at the start** — defining the Status enum in the first data model phase meant all 6 subsequent phases could log without ambiguity. Do this for any project with multi-state pipelines.
2. **Scraper fallback chains need explicit no-op exits** — the `no_email_found` path that continues the run (not raises) was the trickiest behavior to get right; test it explicitly before wiring into the pipeline.
3. **Validate LLM output structurally, not semantically** — word count + placeholder check + cliché list is cheap and reliable; semantic quality checks would require another LLM call. Simple rules cover 95% of bad outputs.
4. **Idempotency via log inspection is more reliable than a seen-set** — reading the CSV log on startup (not maintaining in-memory state) means restarts after a crash automatically resume correctly.

### Cost Observations
- Model mix: ~100% sonnet (balanced profile throughout)
- Sessions: ~12 sessions across 2 days
- Notable: Strict phase dependency ordering kept each session short and focused — no session needed to understand more than 2 phases at once

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~12 | 6 | First project — established TDD RED/GREEN pattern and dependency-ordered phase execution |

### Cumulative Quality

| Milestone | Tests | Coverage | LOC |
|-----------|-------|----------|-----|
| v1.0 | 49 | — | 1,888 Python |

### Top Lessons (Verified Across Milestones)

1. Name all outcome states upfront in the data model — they compound benefit across every downstream phase
2. TDD RED/GREEN atomic commits give instant confidence and eliminate regression uncertainty at phase boundaries
