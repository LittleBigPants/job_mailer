"""Failing test stubs for job_mailer CLI — Phase 2 Wave 0 scaffolds.

These tests import symbols (app with --input flag) that do not yet exist.
They will remain RED until Plan 02-04 wires up the CLI.
"""
import os
import pytest
from typer.testing import CliRunner

from job_mailer.__main__ import app

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
