"""CLI tests for job_mailer — Phase 2 + Phase 3 integration tests."""
import os
from unittest.mock import patch, MagicMock
import pytest
from typer.testing import CliRunner

from job_mailer.__main__ import app
from job_mailer.models import CompanyRecord, Status

runner = CliRunner()


# ---------------------------------------------------------------------------
# CLI --input flag tests
# ---------------------------------------------------------------------------


def test_cli_input_exits_clean(tmp_path, monkeypatch):
    """CLI invoked with --input pointing to a real temp CSV exits with code 0."""
    # Provide the three required env vars so check_env() does not abort
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "test@example.com")

    csv_file = tmp_path / "companies.csv"
    csv_file.write_text("url\nhttps://example.com\n")

    result = runner.invoke(app, ["--input", str(csv_file)])
    assert result.exit_code == 0


def test_cli_missing_input_flag():
    """CLI invoked with no arguments exits with a non-zero exit code."""
    result = runner.invoke(app, [])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Phase 3: scraper integration tests (RED until __main__.py is updated)
# ---------------------------------------------------------------------------


def test_cli_runs_scraper_per_url(tmp_path, monkeypatch):
    """CLI calls scrape_company per URL row and prints a summary line per company."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "test@example.com")

    csv_file = tmp_path / "companies.csv"
    csv_file.write_text("url\nhttps://stripe.com\n")

    mock_record = CompanyRecord(
        url="https://stripe.com",
        company_name="Stripe",
        email_found="jobs@stripe.com",
        status=Status.PENDING,
    )

    with patch("job_mailer.__main__.scrape_company", return_value=mock_record) as mock_scrape:
        result = runner.invoke(app, ["--input", str(csv_file)])

    assert result.exit_code == 0
    assert "Stripe" in result.output
    assert "jobs@stripe.com" in result.output
    mock_scrape.assert_called_once_with("https://stripe.com")
