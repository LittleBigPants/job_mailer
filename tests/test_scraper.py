"""Failing test stubs for job_mailer.scraper — Phase 3 Wave 0 scaffolds.

These tests import scrape_company which does not yet exist (scraper.py not created).
They will remain RED (ImportError) until Plan 03-02 writes the production code.

Coverage:
  DISC-01: email extraction from homepage (mailto link, plain text)
  DISC-02: fallback to /contact page
  DISC-03: fallback to /about page
  DISC-04: no email found case, network failure (SCRAPE_FAILED)
  Support: email priority, excluded addresses, company name inference
"""
import httpx
import pytest

from job_mailer.models import Status
from job_mailer.scraper import scrape_company


# ---------------------------------------------------------------------------
# DISC-01: Homepage email extraction
# ---------------------------------------------------------------------------


def test_homepage_mailto_email(httpx_mock):
    """Extracts email from mailto: link on homepage."""
    httpx_mock.add_response(
        url="https://example.com",
        text='<a href="mailto:jobs@example.com">Contact</a>',
    )
    record = scrape_company("https://example.com")
    assert record.email_found == "jobs@example.com"
    assert record.status == Status.PENDING


def test_homepage_text_email(httpx_mock):
    """Extracts plain-text email found in homepage body."""
    httpx_mock.add_response(
        url="https://example.com",
        text="<p>Reach us at hello@example.com</p>",
    )
    record = scrape_company("https://example.com")
    assert record.email_found == "hello@example.com"


# ---------------------------------------------------------------------------
# DISC-02: /contact fallback
# ---------------------------------------------------------------------------


def test_contact_fallback(httpx_mock):
    """Falls back to /contact when homepage has no email."""
    httpx_mock.add_response(
        url="https://example.com",
        text="<p>No email here</p>",
    )
    httpx_mock.add_response(
        url="https://example.com/contact",
        text='<a href="mailto:contact@example.com">Contact</a>',
    )
    record = scrape_company("https://example.com")
    assert record.email_found == "contact@example.com"


# ---------------------------------------------------------------------------
# DISC-03: /about fallback
# ---------------------------------------------------------------------------


def test_about_fallback(httpx_mock):
    """Falls back to /about when homepage and /contact have no email."""
    httpx_mock.add_response(
        url="https://example.com",
        text="<p>No email here</p>",
    )
    httpx_mock.add_response(
        url="https://example.com/contact",
        text="<p>No email here</p>",
    )
    httpx_mock.add_response(
        url="https://example.com/about",
        text='<a href="mailto:team@example.com">Team</a>',
    )
    record = scrape_company("https://example.com")
    assert record.email_found == "team@example.com"


# ---------------------------------------------------------------------------
# DISC-04: No email found / network failure
# ---------------------------------------------------------------------------


def test_no_email_found(httpx_mock):
    """Returns NO_EMAIL_FOUND when no email exists on any checked page."""
    httpx_mock.add_response(url="https://example.com", text="<p>No email here</p>")
    httpx_mock.add_response(url="https://example.com/contact", text="<p>No email here</p>")
    httpx_mock.add_response(url="https://example.com/about", text="<p>No email here</p>")
    record = scrape_company("https://example.com")
    assert record.email_found == ""
    assert record.status == Status.NO_EMAIL_FOUND


def test_scrape_failed(httpx_mock):
    """Returns SCRAPE_FAILED when network errors prevent any page from loading."""
    httpx_mock.add_exception(httpx.ConnectError("timeout"), url="https://example.com")
    httpx_mock.add_exception(httpx.ConnectError("timeout"), url="https://example.com/contact")
    httpx_mock.add_exception(httpx.ConnectError("timeout"), url="https://example.com/about")
    record = scrape_company("https://example.com")
    assert record.status == Status.SCRAPE_FAILED


# ---------------------------------------------------------------------------
# Support: email priority, exclusion list, company name inference
# ---------------------------------------------------------------------------


def test_email_priority(httpx_mock):
    """Mailto link email is preferred over plain-text email when both appear."""
    httpx_mock.add_response(
        url="https://example.com",
        text='<p>info@example.com</p><a href="mailto:jobs@example.com">Apply</a>',
    )
    record = scrape_company("https://example.com")
    assert record.email_found == "jobs@example.com"


def test_never_return_excluded(httpx_mock):
    """Excluded addresses (noreply@) are never returned as email_found."""
    httpx_mock.add_response(
        url="https://example.com",
        text='<a href="mailto:noreply@example.com">x</a>',
    )
    record = scrape_company("https://example.com")
    assert record.email_found == ""
    assert record.status == Status.NO_EMAIL_FOUND


def test_company_name_inference(httpx_mock):
    """Company name is inferred from domain when no email is found."""
    httpx_mock.add_response(url="https://www.stripe.com", text="<p>No email</p>")
    httpx_mock.add_response(url="https://www.stripe.com/contact", text="<p>No email</p>")
    httpx_mock.add_response(url="https://www.stripe.com/about", text="<p>No email</p>")
    record = scrape_company("https://www.stripe.com")
    assert record.company_name == "Stripe"
