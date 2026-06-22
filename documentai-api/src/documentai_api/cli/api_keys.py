"""CLI for managing API keys."""

from datetime import UTC, datetime
from typing import Annotated

import typer

app = typer.Typer()


@app.command()
def generate(
    api_key_name: Annotated[str, typer.Option(help="Name of the calling system")],
    environment: Annotated[str, typer.Option(help="Deployment environment (e.g. prod, staging)")],
    tenant_id: Annotated[
        str,
        typer.Option(help="Tenant ID to associate with the key"),
    ],
    expires_at: Annotated[
        str | None,
        typer.Option(
            help="Optional expiry date in ISO 8601 format (e.g. 2027-01-01T00:00:00+00:00)"
        ),
    ] = None,
) -> None:
    """Generate an API key, store its hash in DynamoDB, and print the plaintext key.

    The plaintext key is shown once and never stored. Store it securely.
    """
    from documentai_api.utils.auth import generate_api_key

    parsed_expires_at = None
    if expires_at:
        try:
            parsed_expires_at = datetime.fromisoformat(expires_at)
            if parsed_expires_at.tzinfo is None:
                parsed_expires_at = parsed_expires_at.replace(tzinfo=UTC)
        except ValueError:
            typer.echo(f"Error: Invalid expires_at format: {expires_at}", err=True)
            typer.echo("Expected ISO 8601 format, e.g. 2027-01-01T00:00:00+00:00", err=True)
            raise typer.Exit(code=1) from None

    from documentai_api.utils.tenants import get_tenant

    if not get_tenant(tenant_id):
        typer.echo(f"Error: Tenant '{tenant_id}' does not exist.", err=True)
        raise typer.Exit(code=1)

    try:
        api_key, existing_keys = generate_api_key(
            api_key_name=api_key_name,
            environment=environment,
            expires_at=parsed_expires_at,
            tenant_id=tenant_id,
        )
    except Exception as e:
        typer.echo(f"Error: Failed to generate API key: {e}", err=True)
        raise typer.Exit(code=1) from None

    if existing_keys:
        typer.echo("")
        typer.echo(
            f"Warning: {len(existing_keys)} active key(s) already exist for client '{api_key_name}'.",
            err=True,
        )
        typer.echo(
            "The old key(s) remain active. Deactivate them once the client has migrated.",
            err=True,
        )

    typer.echo("")
    typer.echo("API Key (save this - it will not be shown again):")
    typer.echo(f"  {api_key}")
    typer.echo("")
    typer.echo(f"Client:      {api_key_name}")
    typer.echo(f"Environment: {environment}")
    typer.echo(f"Tenant:      {tenant_id}")
    if parsed_expires_at:
        typer.echo(f"Expires:     {parsed_expires_at.isoformat()}")
    else:
        typer.echo("Expires:     never")
    typer.echo("")


@app.command()
def deactivate(
    api_key_name: Annotated[str, typer.Option(help="Name of the calling system")],
    api_key: Annotated[str | None, typer.Option(help="Plaintext API key to deactivate")] = None,
    all_keys: Annotated[
        bool, typer.Option("--all", help="Deactivate all active keys for the client")
    ] = False,
) -> None:
    """Deactivate one or all active API keys for a client."""
    from documentai_api.utils.auth import _hash_key, deactivate_api_key, get_active_keys_by_name

    if not api_key and not all_keys:
        typer.echo("Error: Provide --api-key or --all", err=True)
        raise typer.Exit(code=1) from None

    if api_key and all_keys:
        typer.echo("Error: Provide --api-key or --all, not both", err=True)
        raise typer.Exit(code=1) from None

    if api_key:
        key_hash = _hash_key(api_key)
        deactivated = deactivate_api_key(key_hash)
        if deactivated:
            typer.echo(f"Deactivated key for key: {api_key_name}")
        else:
            typer.echo(f"Error: Key not found for key: {api_key_name}", err=True)
            raise typer.Exit(code=1) from None
    else:
        active_keys = get_active_keys_by_name(api_key_name)
        if not active_keys:
            typer.echo(f"No active keys found for key: {api_key_name}")
            return

        from documentai_api.schemas.api_key import ApiKeyRecord

        for record in active_keys:
            deactivate_api_key(record[ApiKeyRecord.KEY_HASH])

        typer.echo(f"Deactivated {len(active_keys)} key(s) for key: {api_key_name}")


@app.command(name="list")
def list_keys(
    api_key_name: Annotated[str | None, typer.Option(help="Filter by client name")] = None,
    include_inactive: Annotated[
        bool, typer.Option("--include-inactive", help="Include inactive keys")
    ] = False,
) -> None:
    """List API keys, optionally filtered by client. Active keys only by default."""
    from documentai_api.config.env import get_aws_config
    from documentai_api.schemas.api_key import ApiKeyRecord
    from documentai_api.services import ddb as ddb_service
    from documentai_api.utils.auth import get_active_keys_by_name

    try:
        if api_key_name and not include_inactive:
            records = get_active_keys_by_name(api_key_name)
        else:
            table_name = get_aws_config().api_keys_table_name
            if not table_name:
                raise ValueError("API_KEYS_TABLE_NAME environment variable not set")
            all_records = ddb_service.scan(table_name)
            if api_key_name:
                all_records = [
                    r for r in all_records if r.get(ApiKeyRecord.API_KEY_NAME) == api_key_name
                ]
            if not include_inactive:
                all_records = [r for r in all_records if r.get(ApiKeyRecord.IS_ACTIVE, False)]
            records = all_records
    except Exception as e:
        typer.echo(f"Error: Failed to list keys: {e}", err=True)
        raise typer.Exit(code=1) from None

    if not records:
        typer.echo("No keys found.")
        return

    typer.echo("")
    typer.echo(f"{'CLIENT':<30} {'ENV':<12} {'ACTIVE':<8} {'CREATED':<30} {'EXPIRES'}")
    typer.echo("-" * 100)
    for record in records:
        client = record.get(ApiKeyRecord.API_KEY_NAME, "unknown")
        environment = record.get(ApiKeyRecord.ENVIRONMENT, "unknown")
        is_active = record.get(ApiKeyRecord.IS_ACTIVE, False)
        active_cell = typer.style(
            f"{is_active!s:<8}", fg=typer.colors.GREEN if is_active else typer.colors.RED
        )
        created = record.get(ApiKeyRecord.CREATED_AT, "unknown")
        expires = record.get(ApiKeyRecord.EXPIRES_AT, "never")
        typer.echo(f"{client:<30} {environment:<12} {active_cell} {created:<30} {expires}")
    typer.echo("")


if __name__ == "__main__":
    app()
