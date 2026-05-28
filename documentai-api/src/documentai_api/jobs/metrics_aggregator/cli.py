"""CLI entry point for the metrics aggregator job."""

import json

import typer

import documentai_api.logging

app = typer.Typer()


@app.command()
def cli(
    target_date: str = typer.Argument(..., help="Date to aggregate in YYYY-MM-DD format"),
    overwrite: bool = typer.Option(False, help="Overwrite existing aggregation"),
) -> None:
    """Aggregate metrics for a specific date."""
    from documentai_api.jobs.metrics_aggregator.main import main

    with documentai_api.logging.init(__package__):
        result = main(target_date, overwrite=overwrite)
        typer.echo(json.dumps(result, indent=2))


if __name__ == "__main__":
    app()
