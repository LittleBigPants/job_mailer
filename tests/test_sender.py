"""Failing test stubs for job_mailer.sender — Phase 5 Wave 0 scaffolds.

These tests import send_email inside each function body so pytest can collect
them without failing immediately on ImportError. They will remain RED
(ModuleNotFoundError) until Plan 05-02 writes the production code.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
import resend.exceptions

from job_mailer.models import CompanyRecord, Status


def _make_record() -> CompanyRecord:
    """Return a minimal CompanyRecord fixture for sender tests."""
    return CompanyRecord(
        url="https://example.com",
        company_name="Example Corp",
        email_found="ceo@example.com",
        generated_message="Hello, I am reaching out about a role.",
    )


def _make_profile() -> dict:
    """Return a minimal sender profile fixture."""
    return {
        "name": "Alice Dev",
        "email": "alice@sender.example.com",
        "subject_template": "Opportunity at {company_name}",
    }


def test_send_success():
    from job_mailer.sender import send_email

    record = _make_record()
    profile = _make_profile()
    mock_response = MagicMock()
    mock_response.id = "re_abc123"

    with patch("resend.Emails.send", return_value=mock_response):
        send_email(record, profile)

    assert record.status == Status.SENT
    assert record.resend_message_id == "re_abc123"


def test_rate_limit_continues():
    from job_mailer.sender import send_email

    record = _make_record()
    profile = _make_profile()

    exc = resend.exceptions.RateLimitError.__new__(resend.exceptions.RateLimitError)
    exc.error_type = "rate_limit_exceeded"
    exc.message = "rate limit"
    exc.code = 429

    with patch("resend.Emails.send", side_effect=exc):
        send_email(record, profile)  # must not propagate

    assert record.status == Status.RATE_LIMITED


def test_daily_quota_reraises():
    from job_mailer.sender import send_email

    record = _make_record()
    profile = _make_profile()

    exc = resend.exceptions.RateLimitError.__new__(resend.exceptions.RateLimitError)
    exc.error_type = "daily_quota_exceeded"
    exc.message = "quota"
    exc.code = 429

    with patch("resend.Emails.send", side_effect=exc):
        with pytest.raises(resend.exceptions.RateLimitError):
            send_email(record, profile)


def test_send_failed_non_429():
    from job_mailer.sender import send_email

    record = _make_record()
    profile = _make_profile()

    exc = resend.exceptions.ResendError.__new__(resend.exceptions.ResendError)
    exc.message = "internal error"

    with patch("resend.Emails.send", side_effect=exc):
        send_email(record, profile)  # must not propagate

    assert record.status == Status.SEND_FAILED
