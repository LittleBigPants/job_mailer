from __future__ import annotations

import csv
import sys
import time
from pathlib import Path
from typing import Optional

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
    dry_run: bool = typer.Option(False, "--dry-run", help="Scrape and generate but do not send."),
    delay: Optional[int] = typer.Option(None, "--delay", help="Seconds to wait between sends (overrides profile.toml)."),
) -> None:
    """job-mailer: CSV of company URLs -> personalized cold emails."""
    check_env()
    profile = load_profile()
    validate_profile(profile)
    typer.echo(f"Config loaded. Processing: {input}")

    sent_count = 0
    failed_count = 0
    no_email_count = 0
    skipped_count = 0
    would_send_count = 0
    effective_delay = delay if delay is not None else profile.get("send", {}).get("delay_seconds", 2)

    # Idempotency: load already-sent URLs from outreach_log.csv
    log_path = "outreach_log.csv"
    already_sent: set[str] = set()
    if Path(log_path).exists():
        with open(log_path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row.get("status") == "sent":
                    already_sent.add(row["url"])

    # Within-run deduplication set
    seen_urls: set[str] = set()

    with open(input, newline="") as fh:
        reader = csv.reader(fh)
        for row in reader:
            if not row or not row[0].strip():
                continue
            url = row[0].strip()
            if url.lower() == "url":
                continue  # skip header

            # Idempotency + within-run dedup: silently skip already-processed URLs
            if url in already_sent or url in seen_urls:
                skipped_count += 1
                seen_urls.add(url)
                continue
            seen_urls.add(url)

            try:
                record = scrape_company(url)
                if record.email_found:
                    record = generate_email(record, profile)
                if record.generated_message:
                    if dry_run:
                        record.status = Status.DRY_RUN
                        preview = (record.generated_message[:80] + "...") if len(record.generated_message) > 80 else record.generated_message
                        typer.echo(f"[DRY RUN] {record.company_name} — {record.email_found} — {preview}")
                        log_record(record)
                        would_send_count += 1
                    else:
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
            time.sleep(effective_delay)

    if dry_run:
        typer.echo(f"Done (dry run). {would_send_count} would send, {failed_count} failed, {no_email_count} no email found.")
    else:
        typer.echo(f"Done. {sent_count} sent, {skipped_count} skipped, {failed_count} failed, {no_email_count} no email found.")


if __name__ == "__main__":
    app()
