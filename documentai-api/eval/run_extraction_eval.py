"""Eval CLI: submit a document to /v1/admin/extraction-eval and print a field comparison."""

import time

import httpx
import typer

app = typer.Typer()

_POLL_INTERVAL = 10
_POLL_TIMEOUT = 600


def _print_comparison(data: dict) -> None:
    primary_method = data.get("primaryMethod", "primary")
    primary = data.get("primary", {})
    llm = data.get("llm", {})
    all_fields = sorted(set(primary) | set(llm))

    col = 32
    p_label = f"{primary_method.upper()} Value"
    header = f"{'Field':<{col}} {p_label:<25} {'Conf':>8}   {'LLM Value':<25} {'LLM Conf':>8}"
    sep = "=" * len(header)

    typer.echo(f"\n{sep}\n{header}\n{sep}")

    for field in all_fields:
        p = primary.get(field, {})
        lm = llm.get(field, {})
        p_val = str(p.get("value") or "—")[:24]
        llm_val = str(lm.get("value") or "—")[:24]
        p_conf = f"{p['confidence']:.2f}" if p.get("confidence") is not None else "—"
        llm_conf = f"{lm['confidence']:.4f}" if lm.get("confidence") is not None else "—"
        typer.echo(f"{field:<{col}} {p_val:<25} {p_conf:>8}   {llm_val:<25} {llm_conf:>8}")

    typer.echo(sep + "\n")


@app.command()
def run(
    file: str = typer.Option(..., help="Path to the document file"),
    token: str = typer.Option(..., envvar="EVAL_JWT", help="Admin JWT token"),
    base_url: str = typer.Option("http://localhost:8000", envvar="API_BASE_URL"),
) -> None:
    """Run BDA and LLM extraction on a document and compare field output."""
    with open(file, "rb") as f:
        file_bytes = f.read()

    filename = file.split("/")[-1]

    typer.echo(f"Submitting {filename} ({len(file_bytes):,} bytes)...")

    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(base_url=base_url, timeout=30) as client:
        response = client.post(
            "/v1/admin/extraction-eval",
            headers=headers,
            files={"file": (filename, file_bytes)},
        )

    if response.status_code != 202:
        typer.echo(f"Error {response.status_code}: {response.text}", err=True)
        raise typer.Exit(1)

    job_id = response.json()["jobId"]
    typer.echo(f"Job submitted: {job_id}. Waiting for results...")

    deadline = time.monotonic() + _POLL_TIMEOUT
    with httpx.Client(base_url=base_url, timeout=30) as client:
        while time.monotonic() < deadline:
            poll = client.get(
                f"/v1/admin/extraction-eval/{job_id}",
                headers=headers,
            )

            if poll.status_code == 200:
                _print_comparison(poll.json())
                return

            if poll.status_code != 404:
                typer.echo(f"Error {poll.status_code}: {poll.text}", err=True)
                raise typer.Exit(1)

            typer.echo(f"  ...waiting ({int(deadline - time.monotonic())}s remaining)")
            time.sleep(_POLL_INTERVAL)

    typer.echo(f"Timed out after {_POLL_TIMEOUT}s", err=True)
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
