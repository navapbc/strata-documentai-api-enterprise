"""CLI tool to submit a document to /v1/admin/extraction-compare and print a field comparison.

For ad-hoc documents outside the fixture set — see tests/e2e/test_extraction_compare.py for the
fixture-based accuracy report.
"""

from pathlib import Path
from typing import Annotated

import typer

from documentai_api.utils.extraction_compare_client import (
    ExtractionCompareTimeoutError,
    print_comparison,
    submit_and_poll,
)

app = typer.Typer()


@app.command()
def run(
    file: Annotated[Path, typer.Option(help="Path to the document file")],
    token: Annotated[str, typer.Option(envvar="COMPARE_JWT", help="Admin JWT token")],
    base_url: Annotated[str, typer.Option(envvar="API_BASE_URL")] = "http://localhost:8000",
) -> None:
    """Run BDA and LLM extraction on a document and compare field output."""
    if not file.exists():
        typer.echo(f"File not found: {file}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Submitting {file.name} ({file.stat().st_size:,} bytes)...")

    try:
        result = submit_and_poll(base_url, file, token)
    except (ExtractionCompareTimeoutError, RuntimeError) as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from e

    print_comparison(file.name, result, expected=None)


if __name__ == "__main__":
    app()
