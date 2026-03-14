# job-mailer

A single command turns a CSV of company URLs into a batch of personalized, human-sounding cold emails — eliminating the repetitive work of finding contacts and writing intros.

## Quick Start

1. **Clone the repo**
   ```bash
   git clone https://github.com/youruser/job-mailer.git
   cd job-mailer
   ```

2. **Copy and fill in environment variables**
   ```bash
   cp .env.example .env
   # Edit .env — add GROQ_API_KEY, RESEND_API_KEY, RESEND_FROM_EMAIL
   ```

3. **Copy and fill in your developer profile**
   ```bash
   cp profile.example.toml profile.toml
   # Edit profile.toml — add your name, title, skills, etc.
   ```

4. **Complete DNS setup** (see [DNS Setup](#dns-setup-required-before-first-live-send) below)

5. **Run**
   ```bash
   uv pip install -e ".[dev]"
   job-mailer --input companies.csv
   ```

---

## Setup

### Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Groq API key from [console.groq.com](https://console.groq.com) |
| `RESEND_API_KEY` | Resend API key from [resend.com/api-keys](https://resend.com/api-keys) |
| `RESEND_FROM_EMAIL` | The "From" address (must match your verified Resend domain, e.g. `outreach@yourdomain.com`) |

`.env` is gitignored and must never be committed.

### Developer Profile

Copy `profile.example.toml` to `profile.toml` and fill in your details:

```toml
[developer]
name = "Your Name"
title = "Software Engineer"
location = "City, Country"
years_experience = 5

[developer.contact]
email = "you@example.com"
github = "https://github.com/yourhandle"

[developer.skills]
primary = ["Python", "Go", "TypeScript"]
specialisation = "backend APIs and distributed systems"

[send]
delay_seconds = 2
```

`profile.toml` is gitignored and must never be committed.

---

## DNS Setup (Required Before First Live Send)

Before sending any emails, authenticate your sender domain with Resend.
Use a **dedicated subdomain** (e.g., `outreach.yourdomain.com`) — never your primary domain.
Cold email volume can damage sender reputation; keep it isolated.

### Step 1: Add your domain in Resend

1. Go to [Resend Dashboard > Domains](https://resend.com/domains)
2. Click "Add Domain"
3. Enter your sending subdomain (e.g., `outreach.yourdomain.com`)
4. Resend will show you two required DNS records

### Step 2: Add DNS records at your DNS provider

Add the following records (Resend will give you the exact DKIM value):

| Type | Name | Value |
|------|------|-------|
| TXT  | `send` | `v=spf1 include:amazonses.com ~all` |
| TXT  | `resend._domainkey` | *(copy from Resend dashboard — unique per domain)* |
| MX   | `send` | `feedback-smtp.us-east-1.amazonses.com` (priority 10) |

> **SPF** tells receiving servers that Resend's infrastructure is authorized to send on your behalf.
> **DKIM** adds a cryptographic signature Resend generates per domain — copy the value verbatim from the dashboard.

### Step 3: Add DMARC (recommended)

Add a DMARC record to build additional trust with mailbox providers:

| Type | Name | Value |
|------|------|-------|
| TXT  | `_dmarc` | `v=DMARC1; p=none; rua=mailto:dmarc@yourdomain.com` |

Start with `p=none` to monitor without rejecting. Move to `p=quarantine` after reviewing reports.

### Step 4: Verify your records

Check that your SPF, DKIM, and DMARC records are live before running any send:

- [MXToolbox SPF Lookup](https://mxtoolbox.com/spf.aspx)
- [MXToolbox DKIM Lookup](https://mxtoolbox.com/dkim.aspx)
- [MXToolbox DMARC Lookup](https://mxtoolbox.com/dmarc.aspx)

Do not run a live send until Resend shows "Verified" for your domain in the dashboard.

---

## Usage

```bash
# Send emails to all companies in the CSV
job-mailer --input companies.csv

# Dry run — generate emails but do not send
job-mailer --input companies.csv --dry-run

# Slow down send rate (seconds between sends)
job-mailer --input companies.csv --delay 5
```

The `companies.csv` file requires a `url` column. Additional columns (company name, notes) are passed through to the prompt template.

---

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — for virtual env and dependency management
