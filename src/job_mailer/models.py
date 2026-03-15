"""Shared data model for the job-mailer pipeline."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone


class Status(str, enum.Enum):
    """Pipeline status values for a CompanyRecord."""

    PENDING = "pending"
    SENT = "sent"
    NO_EMAIL_FOUND = "no_email_found"
    GENERATION_FAILED = "generation_failed"
    SEND_FAILED = "send_failed"
    RATE_LIMITED = "rate_limited"
    SKIPPED = "skipped"
    SCRAPE_FAILED = "scrape_failed"


@dataclass
class CompanyRecord:
    """A single row in the job-mailer pipeline, representing one target company."""

    url: str
    company_name: str = ""
    email_found: str = ""
    generated_message: str = ""
    status: Status = Status.PENDING
    resend_message_id: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_csv_row(self) -> dict[str, str]:
        """Return a flat dict with all seven LOG-02 fields, suitable for CSV output."""
        return {
            "url": self.url,
            "company_name": self.company_name,
            "email_found": self.email_found,
            "generated_message": self.generated_message,
            "status": self.status.value,
            "resend_message_id": self.resend_message_id,
            "timestamp": self.timestamp,
        }
