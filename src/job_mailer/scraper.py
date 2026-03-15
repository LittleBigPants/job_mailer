"""Web scraper for job_mailer — discovers contact email addresses from company websites."""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

import httpx
import typer
from bs4 import BeautifulSoup

from job_mailer.models import CompanyRecord, Status

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_TIMEOUT = 10.0
_PREFERRED = {"jobs", "hiring", "contact", "hello", "hi", "team"}
_DEPRIORITIZED = {"info", "admin", "support"}
_NEVER_RETURN = {"noreply", "no-reply", "mailer", "donotreply"}
FALLBACK_PATHS = ["", "/contact", "/about"]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _infer_company_name(url: str) -> str:
    """Infer company name from URL by stripping www., taking first domain label, title-casing."""
    netloc = urlparse(url).netloc
    # Remove port if present
    hostname = netloc.split(":")[0]
    # Strip leading www.
    if hostname.startswith("www."):
        hostname = hostname[4:]
    # Take first label (e.g. "stripe" from "stripe.com")
    first_label = hostname.split(".")[0]
    return first_label.title()


def _extract_emails(html: str) -> list[str]:
    """Extract email addresses from HTML via mailto: hrefs and regex on page text.

    Returns a lowercase, deduplicated list preserving insertion order.
    """
    soup = BeautifulSoup(html, "lxml")
    seen: dict[str, None] = {}

    # 1. mailto: hrefs (higher signal — explicit links)
    for tag in soup.find_all("a", href=True):
        href: str = tag["href"]
        if href.lower().startswith("mailto:"):
            address = href[7:].split("?")[0].strip().lower()
            if address and _EMAIL_RE.match(address):
                seen[address] = None

    # 2. Regex scan of visible text
    text = soup.get_text(separator=" ")
    for match in _EMAIL_RE.finditer(text):
        seen[match.group(0).lower()] = None

    return list(seen.keys())


def _score_email(email: str) -> int:
    """Score an email address for selection priority.

    Returns:
        0 — preferred (jobs@, hiring@, contact@, hello@, hi@, team@)
        1 — deprioritized (info@, admin@, support@) or unknown local part
        2 — never return (noreply@, no-reply@, mailer@, donotreply@)
    """
    local = email.split("@")[0].lower()
    if local in _NEVER_RETURN:
        return 2
    if local in _PREFERRED:
        return 0
    return 1


def _best_email(candidates: list[str]) -> str | None:
    """Return the best candidate email or None if all are in the never-return tier."""
    if not candidates:
        return None
    ranked = sorted(candidates, key=_score_email)
    best = ranked[0]
    if _score_email(best) == 2:
        return None
    return best


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scrape_company(url: str) -> CompanyRecord:
    """Scrape a company website and return a CompanyRecord with email discovery results.

    Visits homepage, then /contact, then /about in order.  Accumulates email
    candidates across all pages and selects the best one at the end.  Returns
    early only when a preferred-tier (score 0) email is found mid-loop.

    Args:
        url: The company homepage URL (e.g. "https://stripe.com").

    Returns:
        CompanyRecord with email_found, company_name, and status populated.
    """
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    company_name = _infer_company_name(url)
    record = CompanyRecord(url=url, company_name=company_name)

    all_candidates: list[str] = []
    any_page_succeeded = False

    with httpx.Client(
        headers={"User-Agent": _USER_AGENT},
        timeout=_TIMEOUT,
        follow_redirects=True,
    ) as client:
        for path in FALLBACK_PATHS:
            page_url = url if path == "" else urljoin(base, path)
            try:
                resp = client.get(page_url)
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                typer.echo(f"Warning: failed to fetch {page_url}: {exc}", err=True)
                continue

            if resp.status_code != 200:
                # Non-200: skip page, continue fallback chain
                continue

            any_page_succeeded = True
            page_emails = _extract_emails(resp.text)
            all_candidates.extend(page_emails)

            # Evaluate current candidates after this page
            best = _best_email(all_candidates)
            if best is not None and _score_email(best) == 0:
                # Preferred-tier found — return immediately
                record.email_found = best
                return record
            if all_candidates and best is None:
                # All candidates are never-return — no point visiting more pages
                break

    # Final selection across all pages visited
    best = _best_email(all_candidates)
    if best is not None:
        record.email_found = best
        return record

    # No usable email found
    if not any_page_succeeded:
        record.status = Status.SCRAPE_FAILED
    else:
        record.status = Status.NO_EMAIL_FOUND
    return record
