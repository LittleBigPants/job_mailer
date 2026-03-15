from __future__ import annotations

import csv
from pathlib import Path

import typer

from job_mailer.config import check_env, load_profile, validate_profile
from job_mailer.generator import generate_email
from job_mailer.scraper import scrape_company

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
                    wc = len(record.generated_message.split())
                    typer.echo(f"  {record.company_name} — {record.email_found} — {wc} words — {record.status.value}")
                else:
                    typer.echo(f"  {record.company_name} — {record.email_found or 'no email'} — {record.status.value}")
            except Exception as exc:
                typer.echo(f"  WARNING: failed to scrape {url}: {exc}", err=True)
    typer.echo("Done.")


if __name__ == "__main__":
    app()
