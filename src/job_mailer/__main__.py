from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

import resend.exceptions
import typer

from job_mailer.config import check_env, load_profile, validate_profile
from job_mailer.generator import generate_email
from job_mailer.logger import log_record
from job_mailer.models import Status
from job_mailer.scraper import scrape_company
from job_mailer.sender import send_email

app = typer.Typer()


@app.command()
def main(
    input: Path = typer.Option(
        ...,
        "--input",
        help="Single-column CSV file of company URLs",
        exists=True,
        readable=True,
        file_okay=True,
        dir_okay=False,
    ),
) -> None:
    """job-mailer: CSV of company URLs -> personalized cold emails."""
    check_env()
    profile = load_profile()
    validate_profile(profile)
    typer.echo(f"Config loaded. Processing: {input}")

    sent_count = 0
    failed_count = 0
    no_email_count = 0
    delay = profile.get("send", {}).get("delay_seconds", 2)

    with open(input, newline="") as fh:
        reader = csv.reader(fh)
        for row in reader:
            if not row or not row[0].strip():
                continue
            url = row[0].strip()
            if url.lower() == "url":
                continue  # skip header
            try:
                record = scrape_company(url)
                if record.email_found:
                    record = generate_email(record, profile)
                if record.generated_message:
                    try:
                        record = send_email(record, profile)
                    except resend.exceptions.RateLimitError:
                        log_record(record)
                        typer.echo(
                            f"ERROR: Resend daily quota exceeded. Sent {sent_count} emails this run. Remaining companies not processed.",
                            err=True,
                        )
                        sys.exit(1)
                    log_record(record)
                    if record.status == Status.SENT:
                        typer.echo(f"  {record.company_name} — {record.email_found} — sent")
                        sent_count += 1
                    elif record.status == Status.RATE_LIMITED:
                        typer.echo(
                            f"  WARNING: {record.company_name} — rate_limited (429)",
                            err=True,
                        )
                        failed_count += 1
                    else:
                        failed_count += 1
                else:
                    if record.status in (Status.NO_EMAIL_FOUND, Status.SCRAPE_FAILED):
                        no_email_count += 1
                    elif record.status == Status.GENERATION_FAILED:
                        failed_count += 1
                    log_record(record)
            except resend.exceptions.RateLimitError:
                raise
            except Exception as exc:
                typer.echo(f"  WARNING: failed to scrape {url}: {exc}", err=True)
            time.sleep(delay)

    typer.echo(f"Done. {sent_count} sent, {failed_count} failed, {no_email_count} no email found.")


if __name__ == "__main__":
    app()
