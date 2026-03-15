"""Failing test stubs for job_mailer.logger — Phase 5 Wave 0 scaffolds.

These tests import log_record inside each function body so pytest can collect
them without failing immediately on ImportError. They will remain RED
(ModuleNotFoundError) until Plan 05-02 writes the production code.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from job_mailer.models import CompanyRecord, Status


def _make_record(n: int = 1) -> CompanyRecord:
    """Return a minimal CompanyRecord fixture for logger tests."""
    return CompanyRecord(
        url=f"https://example{n}.com",
        company_name=f"Example Corp {n}",
        email_found=f"ceo{n}@example.com",
        generated_message=f"Hello, reaching out about a role {n}.",
        status=Status.SENT,
        resend_message_id=f"re_{n:03d}",
    )


def test_log_written_immediately(tmp_path):
    from job_mailer.logger import log_record

    record = _make_record()
    log_path = str(tmp_path / "log.csv")

    log_record(record, log_path=log_path)

    assert Path(log_path).exists()


def test_log_appends(tmp_path):
    from job_mailer.logger import log_record

    record1 = _make_record(1)
    record2 = _make_record(2)
    log_path = str(tmp_path / "log.csv")

    log_record(record1, log_path=log_path)
    log_record(record2, log_path=log_path)

    with open(log_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 2


def test_log_fields(tmp_path):
    from job_mailer.logger import log_record

    record = _make_record()
    log_path = str(tmp_path / "log.csv")

    log_record(record, log_path=log_path)

    with open(log_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1
    row = rows[0]
    expected = record.to_csv_row()
    for field, value in expected.items():
        assert field in row, f"Field {field!r} missing from CSV row"
        assert row[field] == value, f"Field {field!r}: expected {value!r}, got {row[field]!r}"


def test_header_written_once(tmp_path):
    from job_mailer.logger import log_record

    record1 = _make_record(1)
    record2 = _make_record(2)
    log_path = str(tmp_path / "log.csv")

    log_record(record1, log_path=log_path)
    log_record(record2, log_path=log_path)

    with open(log_path, newline="") as f:
        lines = f.readlines()

    header_lines = [line for line in lines if line.startswith("url,")]
    assert len(header_lines) == 1
