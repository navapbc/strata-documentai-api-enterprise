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


@app.command()
def backfill(
    start: str = typer.Argument(..., help="Start date in YYYY-MM-DD format"),
    end: str = typer.Argument(..., help="End date in YYYY-MM-DD format"),
    overwrite: bool = typer.Option(False, help="Overwrite existing aggregations"),
) -> None:
    """Rerun aggregations for a date range."""
    from datetime import date, timedelta

    from documentai_api.jobs.metrics_aggregator.main import main

    with documentai_api.logging.init(__package__):
        current = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
        while current <= end_date:
            target = current.isoformat()
            typer.echo(f"Aggregating {target}...")
            result = main(target, overwrite=overwrite)
            typer.echo(json.dumps(result, indent=2))
            current += timedelta(days=1)


if __name__ == "__main__":
    app()
