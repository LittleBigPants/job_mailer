"""CLI tests for job_mailer — Phase 2 + Phase 3 + Phase 4 integration tests."""
import os
import tempfile
from pathlib import Path
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
    """CLI calls scrape_company per URL row and processes each company."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "test@example.com")

    csv_file = tmp_path / "companies.csv"
    csv_file.write_text("url\nhttps://stripe.com\n")

    mock_record = CompanyRecord(
        url="https://stripe.com",
        company_name="Stripe",
        email_found="jobs@stripe.com",
        generated_message="Hello, this is a test email.",
        status=Status.SENT,
        resend_message_id="re_test",
    )

    with (
        patch("job_mailer.__main__.scrape_company", return_value=mock_record) as mock_scrape,
        patch("job_mailer.__main__.generate_email", return_value=mock_record),
        patch("job_mailer.__main__.send_email", return_value=mock_record),
        patch("job_mailer.__main__.log_record"),
        patch("job_mailer.__main__.time"),
    ):
        result = runner.invoke(app, ["--input", str(csv_file)])

    assert result.exit_code == 0
    assert "Stripe" in result.output
    assert "jobs@stripe.com" in result.output
    mock_scrape.assert_called_once_with("https://stripe.com")


# ---------------------------------------------------------------------------
# Phase 4: generator integration tests
# ---------------------------------------------------------------------------


def test_cli_calls_generate_email_after_scrape(tmp_path, monkeypatch):
    """CLI calls generate_email() after a successful scrape when email_found is set."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "test@example.com")

    csv_file = tmp_path / "companies.csv"
    csv_file.write_text("url\nhttps://stripe.com\n")

    scrape_record = CompanyRecord(
        url="https://stripe.com",
        company_name="Stripe",
        email_found="jobs@stripe.com",
        status=Status.PENDING,
    )
    generated_record = CompanyRecord(
        url="https://stripe.com",
        company_name="Stripe",
        email_found="jobs@stripe.com",
        generated_message=(
            "Hello this is a test message with enough words here to pass "
            "the word count validation easily yes it is."
        ),
        status=Status.PENDING,
    )
    minimal_profile = {"developer": {"name": "Test Dev"}}

    sent_record = CompanyRecord(
        url="https://stripe.com",
        company_name="Stripe",
        email_found="jobs@stripe.com",
        generated_message=(
            "Hello this is a test message with enough words here to pass "
            "the word count validation easily yes it is."
        ),
        status=Status.SENT,
        resend_message_id="re_test123",
    )

    with (
        patch("job_mailer.__main__.check_env"),
        patch("job_mailer.__main__.load_profile", return_value=minimal_profile),
        patch("job_mailer.__main__.validate_profile"),
        patch("job_mailer.__main__.scrape_company", return_value=scrape_record),
        patch("job_mailer.__main__.generate_email", return_value=generated_record) as mock_gen,
        patch("job_mailer.__main__.send_email", return_value=sent_record),
        patch("job_mailer.__main__.log_record"),
        patch("job_mailer.__main__.time"),
    ):
        result = runner.invoke(app, ["--input", str(csv_file)])

    assert result.exit_code == 0
    assert mock_gen.called
    # First positional arg to generate_email should be the CompanyRecord
    call_args = mock_gen.call_args
    assert call_args[0][0] is scrape_record


# ---------------------------------------------------------------------------
# Phase 5: send delay integration test
# ---------------------------------------------------------------------------


def test_send_delay_called(tmp_path, monkeypatch):
    """CLI reads delay from profile['send']['delay_seconds'] and calls time.sleep once per row."""
    from job_mailer.models import CompanyRecord, Status

    csv_file = tmp_path / "companies.csv"
    csv_file.write_text("url\nhttps://example.com\n")

    mock_record_scraped = CompanyRecord(
        url="https://example.com",
        company_name="Example",
        email_found="ceo@example.com",
    )
    mock_record_generated = CompanyRecord(
        url="https://example.com",
        company_name="Example",
        email_found="ceo@example.com",
        generated_message="Hello, I am reaching out.",
    )
    mock_record_sent = CompanyRecord(
        url="https://example.com",
        company_name="Example",
        email_found="ceo@example.com",
        generated_message="Hello, I am reaching out.",
        status=Status.SENT,
        resend_message_id="re_abc",
    )

    monkeypatch.setenv("RESEND_API_KEY", "test_key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "from@test.com")
    monkeypatch.setenv("GROQ_API_KEY", "test_groq")

    with (
        patch("job_mailer.__main__.scrape_company", return_value=mock_record_scraped),
        patch("job_mailer.__main__.generate_email", return_value=mock_record_generated),
        patch("job_mailer.__main__.send_email", return_value=mock_record_sent),
        patch("job_mailer.__main__.log_record"),
        patch("job_mailer.__main__.time") as mock_time,
        patch("job_mailer.__main__.load_profile", return_value={"send": {"delay_seconds": 3}}),
        patch("job_mailer.__main__.validate_profile"),
    ):
        from typer.testing import CliRunner
        from job_mailer.__main__ import app
        runner_local = CliRunner()
        result = runner_local.invoke(app, ["--input", str(csv_file)])

    assert result.exit_code == 0
    mock_time.sleep.assert_called_once_with(3)
