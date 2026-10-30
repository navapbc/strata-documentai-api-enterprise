"""CLI tools for extraction compare.

run-extraction-compare-file     — submit a single ad-hoc document and print results
run-extraction-compare-fixtures — run all compareEnabled fixture documents and write reports
"""

import asyncio
import json
import time
from contextlib import nullcontext, suppress
from pathlib import Path
from typing import Annotated

import jwt
import typer

from documentai_api.cli.extraction_compare import (
    write_comparison_md,
    write_extraction_compare_summary,
)
from documentai_api.cli.extraction_compare.comparison import (
    _load_expected,
    _load_expected_geometry,
)
from documentai_api.config.env import get_env_config
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.services import ddb as ddb_service
from documentai_api.services import s3 as s3_service
from documentai_api.utils.extraction_compare_client import (
    ExtractionCompareTimeoutError,
    cognito_jwt,
    print_comparison,
    processing_span_seconds,
    submit_and_poll,
)
from documentai_api.utils.s3 import parse_s3_uri

file_app = typer.Typer()
fixtures_app = typer.Typer()

_PROJECT_ROOT = next(p for p in Path(__file__).parents if (p / "pyproject.toml").exists())
_FIXTURES_DIR = _PROJECT_ROOT / "tests" / "helpers" / "fixtures" / "test-documents"
_EXPECTED_DIR = _FIXTURES_DIR / "happy-path" / "expected"
_TEST_DOCS_DIR = _FIXTURES_DIR / "happy-path"
_RESULTS_DIR = _PROJECT_ROOT / "tests" / "results" / "extraction_compare"
_RUN_ALL_CONCURRENCY_LIMIT = 6


@file_app.command()
def run_file(
    file: Annotated[Path, typer.Option(help="Path to the document file")],
    token: Annotated[str, typer.Option(envvar="COMPARE_JWT", help="Admin JWT token")],
    base_url: Annotated[str, typer.Option(envvar="API_BASE_URL")] = "http://localhost:8000",
) -> None:
    """Run BDA and LLM extraction on a document and print a field comparison."""
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


@fixtures_app.command()
def run_fixtures(
    token: Annotated[
        str | None,
        typer.Option(
            envvar="COMPARE_JWT", help="Admin JWT token (auto-generated from Cognito if omitted)"
        ),
    ] = None,
    base_url: Annotated[str, typer.Option(envvar="API_BASE_URL")] = "http://localhost:8000",
    results_dir: Annotated[Path, typer.Option(help="Directory to write results")] = _RESULTS_DIR,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Print per-field comparison tables")
    ] = False,
) -> None:
    """Run extraction compare for all compareEnabled fixture documents and write reports."""
    cfg = get_env_config()
    user_pool_id = cfg.cognito_user_pool_id
    client_id = cfg.cognito_client_id
    region = cfg.aws_region

    token_ctx = (
        cognito_jwt(user_pool_id, client_id, region)
        if (not token and user_pool_id and client_id)
        else nullcontext(token)
    )

    with token_ctx as resolved_token:
        if not resolved_token:
            typer.echo(
                "No token: set COMPARE_JWT or COGNITO_USER_POOL_ID + COGNITO_CLIENT_ID.", err=True
            )
            raise typer.Exit(1)

        sub = jwt.decode(resolved_token, options={"verify_signature": False}).get("sub", "unknown")
        compare_tenant = f"compare-{sub}"
        _wipe_compare_tenant(compare_tenant)

        cases = json.loads((_FIXTURES_DIR / "expected.json").read_text())
        filenames = [
            Path(f).name for f, entry in cases.items() if entry.get("compareEnabled", False)
        ]

        if not filenames:
            typer.echo("No compareEnabled fixtures found.", err=True)
            raise typer.Exit(1)

        md_dir = results_dir / "md"
        data_dir = results_dir / "data"

        wall_start = time.monotonic()
        timings = asyncio.run(
            _run_all(filenames, base_url, resolved_token, md_dir, data_dir, verbose)
        )
        wall = time.monotonic() - wall_start

        col = max(len(f) for f in filenames)
        typer.echo("")
        for filename in sorted(timings):
            elapsed, error = timings[filename]
            if error:
                status = typer.style("FAILED", fg=typer.colors.RED)
                typer.echo(f"{filename:<{col}}  {status}  {elapsed:>6.1f}s ({error})")
            else:
                status = typer.style("PASSED", fg=typer.colors.GREEN)
                typer.echo(f"{filename:<{col}}  {status}  {elapsed:>6.1f}s")

        n_fail = sum(1 for _, err in timings.values() if err)
        typer.echo(f"{'─' * (col + 30)}")
        n_ok = len(filenames) - n_fail
        ok_str = typer.style(str(n_ok), fg=typer.colors.GREEN)
        fail_str = typer.style(str(n_fail), fg=typer.colors.RED if n_fail else typer.colors.GREEN)
        summary = f"{ok_str} completed, {fail_str} failed  |  wall: {wall:.1f}s"
        typer.echo(summary)
        typer.echo("")

        typer.echo("Writing summary...")
        write_extraction_compare_summary(results_dir, _EXPECTED_DIR)
        typer.echo("Done.")

        _wipe_compare_tenant(compare_tenant)

        if n_fail:
            raise typer.Exit(1)


async def _run_all(
    filenames: list[str],
    base_url: str,
    token: str,
    md_dir: Path,
    data_dir: Path,
    verbose: bool = False,
) -> dict[str, tuple[float, str | None]]:
    sem = asyncio.Semaphore(_RUN_ALL_CONCURRENCY_LIMIT)

    async def _file(filename: str) -> tuple[str, float, str | None]:
        async with sem:
            t0 = time.monotonic()
            typer.echo(f"Submitting {filename}...")
            try:
                result = None
                for attempt in range(2):
                    try:
                        result = await asyncio.to_thread(
                            submit_and_poll, base_url, _TEST_DOCS_DIR / filename, token
                        )
                        break
                    except (ExtractionCompareTimeoutError, RuntimeError):
                        if attempt == 1:
                            raise
                        typer.echo(f"  - Retrying {filename}...", err=True)

                if result is None:
                    raise RuntimeError("no result after retry")

                expected = _load_expected(filename, _EXPECTED_DIR)

                if verbose:
                    print_comparison(filename, result, expected)

                write_comparison_md(
                    filename,
                    result,
                    expected,
                    _load_expected_geometry(filename, _EXPECTED_DIR),
                    md_dir=md_dir,
                    data_dir=data_dir,
                )
                typer.echo(f"  - Wrote {md_dir / Path(filename).stem}.md")
                elapsed = processing_span_seconds(result) or time.monotonic() - t0
                return filename, elapsed, None
            except Exception as e:
                typer.echo(f"  ERROR: {e}", err=True)
                return filename, time.monotonic() - t0, str(e)

    return {f: (e, err) for f, e, err in await asyncio.gather(*(_file(f) for f in filenames))}


def _wipe_compare_tenant(tenant_id: str) -> None:
    cfg = get_env_config()
    if not (
        cfg.documentai_document_metadata_table_name
        and cfg.documentai_document_metadata_tenant_index_name
        and cfg.documentai_input_location
    ):
        return

    bucket, prefix = parse_s3_uri(cfg.documentai_input_location)

    for record in ddb_service.query_by_key(
        cfg.documentai_document_metadata_table_name,
        cfg.documentai_document_metadata_tenant_index_name,
        DocumentMetadata.TENANT_ID,
        tenant_id,
    ):
        key = record.get(DocumentMetadata.FILE_NAME)
        if key:
            s3_key = f"{prefix}/{tenant_id}/{key}" if prefix else f"{tenant_id}/{key}"
            with suppress(Exception):
                s3_service.delete_object(bucket, s3_key)

        with suppress(Exception):
            ddb_service.delete_item(
                cfg.documentai_document_metadata_table_name,
                {DocumentMetadata.FILE_NAME: record[DocumentMetadata.FILE_NAME]},
            )


if __name__ == "__main__":
    file_app()
