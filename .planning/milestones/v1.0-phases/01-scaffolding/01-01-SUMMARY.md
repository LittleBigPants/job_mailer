---
phase: 01-scaffolding
plan: 01
subsystem: infra
tags: [python, pyproject.toml, uv, hatchling, gitignore, dotenv, typer]

# Dependency graph
requires: []
provides:
  - pyproject.toml with all runtime and dev dependencies and job-mailer CLI entry point
  - src/job_mailer Python package (importable via `import job_mailer`)
  - .gitignore preventing .env and profile.toml from ever being tracked
  - .env.example documenting GROQ_API_KEY, RESEND_API_KEY, RESEND_FROM_EMAIL
  - .venv with all dependencies installed via uv
affects:
  - 01-02 (profile schema — needs importable package)
  - All future phases (all build on this package skeleton)

# Tech tracking
tech-stack:
  added:
    - typer>=0.24.1 (CLI framework)
    - httpx>=0.28.1 (HTTP client)
    - beautifulsoup4>=4.14.3 (HTML parsing)
    - lxml>=6.0.2 (HTML parser backend)
    - groq>=1.1.1 (Groq LLM API client)
    - resend>=2.23.0 (email delivery SDK)
    - tenacity>=9.1.4 (retry logic)
    - python-dotenv>=1.0 (env var loading)
    - pytest (test runner, dev dep)
    - ruff (linter/formatter, dev dep)
    - hatchling (build backend)
    - uv (package manager + venv)
  patterns:
    - src layout (src/job_mailer/) for clean packaging
    - pyproject.toml as single dependency manifest (no requirements.txt)
    - .gitignore committed before ignored files exist (prevents accidental secret commits)
    - .env.example as committed schema reference alongside gitignored .env

key-files:
  created:
    - pyproject.toml
    - .gitignore
    - .env.example
    - src/job_mailer/__init__.py
    - src/job_mailer/__main__.py
  modified: []

key-decisions:
  - "uv installed via pip --user --break-system-packages (not in PATH by default on this system; venv created via .venv/bin/ paths)"
  - "src layout chosen for clean editable install separation from repo root"
  - ".gitignore created as first committed file before any ignored files to prevent accidental staging"

patterns-established:
  - "Pattern 1: src/job_mailer/ package layout — all source code lives under src/"
  - "Pattern 2: .gitignore before secrets — gitignore must exist before any file it ignores is created"
  - "Pattern 3: .env.example as committed schema — all required env vars documented in example file, real values only in gitignored .env"

requirements-completed: [INFRA-02]

# Metrics
duration: 2min
completed: 2026-03-14
---

# Phase 1 Plan 01: Project Skeleton Summary

**Python package skeleton with pyproject.toml (all 8 runtime deps + dev tools), src/job_mailer layout, gitignored secrets, and .env.example for GROQ/Resend keys**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-14T19:47:13Z
- **Completed:** 2026-03-14T19:49:01Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Created pyproject.toml with all 8 runtime dependencies, CLI entry point, ruff config, and pytest config
- Created src/job_mailer package (importable, minimal Typer CLI stub at entry point)
- Established .gitignore (committing .env and profile.toml exclusions before any such files exist)
- Created .env.example documenting all three required API keys
- Installed .venv with all runtime and dev dependencies via uv

## Task Commits

Each task was committed atomically:

1. **Task 1: Create project skeleton and gitignore** - `b0f9376` (feat)
2. **Task 2: Create .env.example** - `cdb06df` (feat)

**Plan metadata:** *(docs commit - see below)*

## Files Created/Modified
- `pyproject.toml` - Project metadata, all dependencies, CLI entry point, ruff/pytest config
- `.gitignore` - Excludes .env, profile.toml, __pycache__, .venv, dist, IDE dirs
- `src/job_mailer/__init__.py` - Makes job_mailer an importable Python package
- `src/job_mailer/__main__.py` - Minimal Typer app stub (`job-mailer` CLI entry point)
- `.env.example` - Documents GROQ_API_KEY, RESEND_API_KEY, RESEND_FROM_EMAIL with placeholder values

## Decisions Made
- **uv installed via pip with --break-system-packages:** uv was not present on the system; installed via `pip install uv --user --break-system-packages` (Rule 3 auto-fix — blocking dependency). This is safe on Arch Linux for user-local tool installs.
- **src layout used:** Isolates package from root-level scripts; enables clean editable installs via hatchling.
- **RESEND_FROM_EMAIL stays in .env:** Per REQUIREMENTS.md and RESEARCH.md recommendation — even though it is not strictly a secret, the requirements spec places it alongside API keys in .env.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing uv dependency**
- **Found during:** Task 1 (venv creation)
- **Issue:** `uv` command not found — not installed on the system
- **Fix:** Installed via `pip install uv --user --break-system-packages`; venv creation then succeeded
- **Files modified:** ~/.local/bin/uv (system-level user install, not tracked in repo)
- **Verification:** `uv --version` returns 0.10.10; `uv venv` and `uv pip install -e ".[dev]"` succeeded
- **Committed in:** Not committed (tool install, not source change)

---

**Total deviations:** 1 auto-fixed (1 blocking — missing tool)
**Impact on plan:** Required uv to be available to execute the plan commands. No scope creep; no source files changed beyond the plan.

## Issues Encountered
None beyond the uv installation — all 37 packages resolved and installed cleanly.

## User Setup Required
None - no external service configuration required at this stage.

## Next Phase Readiness
- Python package is importable: `import job_mailer` works
- All runtime and dev dependencies installed in .venv
- Secrets infrastructure in place: .env is gitignored, .env.example is committed
- Ready for Plan 02 (profile schema) and subsequent phases
- No blockers

## Self-Check: PASSED

- FOUND: pyproject.toml
- FOUND: .gitignore
- FOUND: .env.example
- FOUND: src/job_mailer/__init__.py
- FOUND: src/job_mailer/__main__.py
- FOUND commit: b0f9376 (feat(01-01): create project skeleton and gitignore)
- FOUND commit: cdb06df (feat(01-01): add .env.example documenting all required API keys)

---
*Phase: 01-scaffolding*
*Completed: 2026-03-14*
