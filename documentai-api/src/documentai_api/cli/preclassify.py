"""CLI tool for testing preclassification against a real document."""

import mimetypes
from pathlib import Path
from typing import Annotated

import typer

from documentai_api.utils.preclassification import preclassify_document

app = typer.Typer()


@app.command()
def main(
    file: Annotated[Path, typer.Argument(help="Path to document (PDF, JPEG, PNG, etc.)")],
    category: Annotated[
        str | None, typer.Option("--category", "-c", help="User-provided category")
    ] = None,
) -> None:
    if not file.exists():
        typer.echo(f"File not found: {file}", err=True)
        raise typer.Exit(1)

    content_type, _ = mimetypes.guess_type(str(file))
    if not content_type:
        typer.echo(f"Could not determine content type for: {file}", err=True)
        raise typer.Exit(1)

    typer.echo(f"File:          {file.name}")
    typer.echo(f"Content-Type:  {content_type}")
    typer.echo(f"Category:      {category or '(none)'}")
    typer.echo("")

    result = preclassify_document(file.read_bytes(), content_type, category)

    typer.echo(f"document_type:       {result.document_type}")
    typer.echo(f"confidence:          {result.confidence}")
    typer.echo(f"document_count:      {result.document_count}")
    typer.echo(f"category_match:      {result.category_match}")
    typer.echo(f"is_identity_document:{result.is_identity_document}")
    typer.echo(f"model_id:            {result.model_id}")
    typer.echo(f"duration_seconds:    {result.duration_seconds}s")
    typer.echo(f"tokens (in/out):     {result.input_tokens}/{result.output_tokens}")


if __name__ == "__main__":
    app()
