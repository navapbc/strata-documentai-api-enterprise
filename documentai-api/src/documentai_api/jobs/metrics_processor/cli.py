"""CLI entry point for the metrics processor job."""

import typer

import documentai_api.logging

app = typer.Typer()


@app.command()
def cli(
    queue_url: str = typer.Argument(..., help="SQS queue URL to consume from"),
    bucket_name: str = typer.Argument(..., help="S3 bucket for writing metrics data"),
    max_messages: int = typer.Option(10, help="Max messages per batch"),
    max_batches: int = typer.Option(10, help="Max batches to process"),
) -> None:
    """Process metrics from SQS queue and write to S3."""
    from documentai_api.jobs.metrics_processor.main import main

    with documentai_api.logging.init(__package__):
        total = main(queue_url, bucket_name, max_messages, max_batches)
        typer.echo(f"Processed {total} messages")


if __name__ == "__main__":
    app()
