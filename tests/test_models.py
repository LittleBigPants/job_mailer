"""Failing test stubs for job_mailer.models — Phase 2 Wave 0 scaffolds.

These tests import symbols that do not yet exist (models.py not created).
They will remain RED (ImportError) until Plan 02-02 writes the production code.
"""
import pytest

from job_mailer.models import CompanyRecord, Status


# ---------------------------------------------------------------------------
# CompanyRecord tests
# ---------------------------------------------------------------------------


def test_company_record_defaults():
    """CompanyRecord instantiated with only a URL uses correct default values."""
    record = CompanyRecord("https://example.com")
    assert record.url == "https://example.com"
    assert record.company_name == ""
    assert record.email_found == ""
    assert record.generated_message == ""
    assert record.status == Status.PENDING
    assert record.resend_message_id == ""
    assert isinstance(record.timestamp, str) and record.timestamp != ""


def test_company_record_fields():
    """CompanyRecord has exactly the expected set of attributes."""
    expected_fields = {
        "url",
        "company_name",
        "email_found",
        "generated_message",
        "status",
        "resend_message_id",
        "timestamp",
    }
    record = CompanyRecord("https://example.com")
    actual_fields = set(vars(record).keys())
    assert actual_fields == expected_fields


# ---------------------------------------------------------------------------
# Status enum tests
# ---------------------------------------------------------------------------


def test_status_enum_values():
    """Status enum exposes exactly the required .value strings."""
    expected_values = {
        "pending",
        "sent",
        "no_email_found",
        "generation_failed",
        "send_failed",
        "skipped",
        "scrape_failed",
    }
    actual_values = {member.value for member in Status}
    assert actual_values == expected_values
