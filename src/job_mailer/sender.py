"""Email sender module — dispatches personalized emails via the Resend API."""
from __future__ import annotations

import os

import resend
import resend.exceptions

from job_mailer.models import CompanyRecord, Status


def send_email(record: CompanyRecord, profile: dict) -> CompanyRecord:
    """Send a personalized email for *record* using the Resend API.

    Sets record.status and record.resend_message_id in-place and returns
    the record. Only raises on daily_quota_exceeded — all other expected
    Resend errors are caught and reflected in record.status.
    """
    resend.api_key = os.environ.get("RESEND_API_KEY", "")
    from_email = os.environ.get("RESEND_FROM_EMAIL", "")

    params: resend.Emails.SendParams = {
        "from": from_email,
        "to": [record.email_found],
        "subject": f"Reaching out \u2014 {record.company_name}",
        "text": record.generated_message,
    }

    try:
        response = resend.Emails.send(params)
        record.resend_message_id = response.id
        record.status = Status.SENT
    except resend.exceptions.RateLimitError as exc:
        record.status = Status.RATE_LIMITED
        if exc.error_type == "daily_quota_exceeded":
            raise
    except resend.exceptions.ResendError:
        record.status = Status.SEND_FAILED

    return record
