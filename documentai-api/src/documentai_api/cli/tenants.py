"""CLI for managing tenants."""

from typing import Annotated

import typer

app = typer.Typer()


@app.command()
def create(
    tenant_id: Annotated[str, typer.Option(help="Unique tenant identifier")],
    display_name: Annotated[str, typer.Option(help="Human-readable tenant name")],
    primary_contact: Annotated[str | None, typer.Option(help="Primary contact email")] = None,
    extraction_confidence_floor: Annotated[
        float | None, typer.Option(help="Minimum extraction confidence threshold")
    ] = None,
) -> None:
    """Create a new tenant in DynamoDB."""
    from documentai_api.utils.tenants import create_tenant

    try:
        record = create_tenant(
            tenant_id=tenant_id,
            display_name=display_name,
            primary_contact=primary_contact,
            extraction_confidence_floor=extraction_confidence_floor,
        )
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from None

    typer.echo("")
    typer.echo(f"Tenant created: {record['tenantId']}")
    typer.echo(f"  Display name: {record['displayName']}")
    if primary_contact:
        typer.echo(f"  Contact:      {primary_contact}")
    typer.echo("")


@app.command(name="list")
def list_tenants(
    include_inactive: Annotated[
        bool, typer.Option("--include-inactive", help="Include inactive tenants")
    ] = False,
) -> None:
    """List all tenants."""
    from documentai_api.schemas.tenants import TenantRecord
    from documentai_api.utils.tenants import list_tenants as _list_tenants

    records = _list_tenants(active_only=not include_inactive)
    if not records:
        typer.echo("No tenants found.")
        return

    def fit(value: object, width: int) -> str:
        """Pad or truncate (with ellipsis) a value to exactly `width` columns."""
        s = str(value)
        return s.ljust(width) if len(s) <= width else s[: width - 1] + "…"

    typer.echo("")
    typer.echo(f"{'TENANT ID':<30} {'DISPLAY NAME':<30} {'ACTIVE':<8} {'CREATED'}")
    typer.echo("-" * 90)
    for r in records:
        is_active = r.get(TenantRecord.IS_ACTIVE, True)
        active_cell = typer.style(
            f"{is_active!s:<8}", fg=typer.colors.GREEN if is_active else typer.colors.RED
        )
        typer.echo(
            f"{fit(r.get(TenantRecord.TENANT_ID, ''), 30)} "
            f"{fit(r.get(TenantRecord.DISPLAY_NAME, ''), 30)} "
            f"{active_cell} "
            f"{r.get(TenantRecord.CREATED_AT, 'unknown')}"
        )
    typer.echo("")


@app.command()
def deactivate(
    tenant_id: Annotated[str, typer.Option(help="Tenant ID to deactivate")],
) -> None:
    """Soft-delete a tenant."""
    from documentai_api.utils.tenants import deactivate_tenant

    if deactivate_tenant(tenant_id):
        typer.echo(f"Deactivated tenant: {tenant_id}")
    else:
        typer.echo(f"Error: Tenant '{tenant_id}' not found or already inactive.", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
