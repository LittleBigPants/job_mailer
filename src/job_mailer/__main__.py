from __future__ import annotations

from pathlib import Path

import typer

from job_mailer.config import check_env, load_profile, validate_profile

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
    # Pipeline not yet implemented — later phases add logic here
    typer.echo(f"Config loaded. Input file: {input}")


if __name__ == "__main__":
    app()
