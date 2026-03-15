"""CSV logger module — appends one row per outreach record immediately after sending."""
from __future__ import annotations

import csv
from pathlib import Path

from job_mailer.models import CompanyRecord

_FIELDS = [
    "url",
    "company_name",
    "email_found",
    "generated_message",
    "status",
    "resend_message_id",
    "timestamp",
]


def log_record(record: CompanyRecord, log_path: str = "outreach_log.csv") -> None:
    """Append *record* as a single CSV row to *log_path*, flushing immediately.

    Creates the file with a header row on first call. Subsequent calls append
    data rows only — the header is written exactly once.
    """
    write_header = not Path(log_path).exists()

    with open(log_path, mode="a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(record.to_csv_row())
        fh.flush()
