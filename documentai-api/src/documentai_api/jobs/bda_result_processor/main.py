#!/usr/bin/env python3
"""Process BDA output from S3 and extract document data."""

import json
from typing import Any

import typer

import documentai_api.logging
from documentai_api.utils.bda_output_processor import process_bda_output

logger = documentai_api.logging.get_logger(__name__)
app = typer.Typer()


def main(bucket_name: str, object_key: str) -> dict[str, Any]:
    """Process BDA output file.

    Args:
        bucket_name: S3 bucket containing BDA output
        object_key: S3 object key of BDA output file

    Returns:
        API response data dictionary
    """
    logger.info(f"Processing BDA output: s3://{bucket_name}/{object_key}")

    # only process BDA output job metadata files
    if not object_key.endswith("job_metadata.json"):
        logger.info(f"Skipping non-metadata file: {object_key}")
        return {}

    result = process_bda_output(bucket_name, object_key)
    logger.info(f"Successfully processed BDA output for s3://{bucket_name}/{object_key}")

    return result


@app.command()
def cli(
    bucket_name: str = typer.Argument(..., help="S3 bucket containing BDA output"),
    object_key: str = typer.Argument(..., help="S3 object key of BDA output file"),
) -> None:
    """Process BDA output file."""
    with documentai_api.logging.init(__package__):
        try:
            result = main(bucket_name, object_key)
            if result:
                typer.echo(json.dumps(result))
        except Exception:
            raise typer.Exit(1) from None


if __name__ == "__main__":
    app()
