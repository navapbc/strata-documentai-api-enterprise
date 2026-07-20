"""CLI entry point for the usage report job."""

import json

import typer

import documentai_api.logging

app = typer.Typer()


@app.command()
def cli(
    month: str = typer.Argument(..., help="Target month (YYYY-MM)"),
) -> None:
    """Generate monthly tenant usage report."""
    from documentai_api.jobs.usage_report.main import main

    with documentai_api.logging.init(__package__):
        result = main(month)
        typer.echo(json.dumps(result, indent=2))


if __name__ == "__main__":
    app()
