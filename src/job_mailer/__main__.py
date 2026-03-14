import typer

app = typer.Typer()


@app.command()
def main() -> None:
    """job-mailer: CSV of company URLs -> personalized cold emails."""
    typer.echo("job-mailer: not yet implemented")


if __name__ == "__main__":
    app()
