"""CLI to preload BDA blueprint schemas into a static JSON file.

Blueprint schemas rarely change, so instead of calling BDA's
GetDataAutomationProject/GetBlueprint at request time - which throttles under
load - get_all_schemas() reads a static file this CLI generates offline.
Re-run this and redeploy whenever blueprints change (a new document type, or
an edited custom blueprint).
"""

import dataclasses
import json
from pathlib import Path

import typer

from documentai_api.utils.schemas import DocumentSchema

app = typer.Typer()

_INFRA_DOCUMENT_TYPES = Path(__file__).resolve().parents[4] / "infra" / "document-types"


@app.command()
def write() -> None:
    """Fetch all blueprint schemas from BDA and write them to the static schemas file."""
    from documentai_api.utils.schemas import SCHEMAS_FILE, fetch_schemas_from_bda

    def report_progress(category: str, category_schemas: dict[str, DocumentSchema]) -> None:
        if category_schemas:
            names = ", ".join(sorted(category_schemas))
            typer.echo(f"  {category}: {len(category_schemas)} ({names})")
        else:
            typer.echo(f"  {category}: failed - see logs")

    typer.echo("Fetching blueprint schemas from BDA...")
    schemas = fetch_schemas_from_bda(on_category=report_progress)

    if not schemas:
        typer.echo("Error: no schemas fetched from BDA.", err=True)
        raise typer.Exit(code=1)

    data = {doc_type: dataclasses.asdict(schema) for doc_type, schema in schemas.items()}

    SCHEMAS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCHEMAS_FILE.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

    typer.echo(f"Wrote {len(schemas)} schemas to {SCHEMAS_FILE}")


@app.command()
def check() -> None:
    """Verify blueprint_schemas.json matches infra/document-types/.

    Three checks, all using only local files (no AWS access):

    1. Custom blueprints: exact content match (fields/description/category).
    2. Managed blueprints: a per-category *count* match against
       managed_blueprints.json. A managed blueprint's own document type name is
       assigned by AWS and doesn't match managed_blueprints.json's `name` field
       (e.g. "us-driver-license" becomes "US-drivers-licenses"), so identity
       can't be verified locally - this only catches an added/removed managed
       blueprint changing the count, not a same-category swap.
    3. Orphaned categories: entries tagged with a category that no longer
       exists under infra/document-types/ at all.

    Run in CI to catch a blueprint change committed without a corresponding
    `pull-blueprint-schemas write` re-run.
    """
    from documentai_api.utils.schemas import SCHEMAS_FILE, SchemaField, extract_fields

    if not SCHEMAS_FILE.exists():
        typer.echo(
            f"Error: {SCHEMAS_FILE} not found - run 'pull-blueprint-schemas write'.", err=True
        )
        raise typer.Exit(code=1)

    committed = json.loads(SCHEMAS_FILE.read_text())

    problems: list[str] = []
    current_categories = {p.name for p in _INFRA_DOCUMENT_TYPES.iterdir() if p.is_dir()}

    for category_dir in sorted(p for p in _INFRA_DOCUMENT_TYPES.iterdir() if p.is_dir()):
        category = category_dir.name
        custom_document_types: set[str] = set()

        for custom_file in sorted(category_dir.glob("custom-*.json")):
            schema = json.loads(custom_file.read_text())
            document_type = schema.get("class")
            if not document_type:
                # No local fallback here that matches the real fetch path - BDA falls back to
                # the blueprint's registered name, which this check has no way to know.
                problems.append(f"{custom_file}: missing required 'class' field")
                continue
            custom_document_types.add(document_type)

            # Field order isn't meaningful - BDA doesn't preserve the JSON file's
            # property insertion order, so both sides are sorted by name before comparing.
            expected = DocumentSchema(
                document_type=document_type,
                description=schema.get("description", ""),
                fields=sorted(extract_fields(schema), key=lambda f: f.name),
                category=category,
            )

            entry = committed.get(document_type)
            if entry is None:
                problems.append(
                    f"{document_type} ({custom_file}): missing from {SCHEMAS_FILE.name}"
                )
                continue

            actual = DocumentSchema(
                document_type=entry["document_type"],
                description=entry["description"],
                fields=sorted((SchemaField(**f) for f in entry["fields"]), key=lambda f: f.name),
                category=entry["category"],
            )

            if actual != expected:
                problems.append(
                    f"{document_type} ({custom_file}): out of sync with {SCHEMAS_FILE.name}"
                )

        managed_file = category_dir / "managed_blueprints.json"
        expected_managed_count = (
            len(json.loads(managed_file.read_text())) if managed_file.exists() else 0
        )
        actual_managed_count = sum(
            1
            for doc_type, entry in committed.items()
            if entry["category"] == category and doc_type not in custom_document_types
        )
        if actual_managed_count != expected_managed_count:
            problems.append(
                f"{category}: managed_blueprints.json lists {expected_managed_count} "
                f"blueprint(s), but {SCHEMAS_FILE.name} has {actual_managed_count} entries not "
                "accounted for by a custom blueprint - a managed blueprint may have been "
                "added/removed, or a custom blueprint deleted, without re-running "
                "pull-blueprint-schemas"
            )

    orphaned_categories = {entry["category"] for entry in committed.values()} - current_categories
    problems.extend(
        f"{category}: no longer exists under infra/document-types/, but "
        f"{SCHEMAS_FILE.name} still has entries tagged with it"
        for category in sorted(orphaned_categories)
    )

    if problems:
        typer.echo("blueprint_schemas.json is out of sync with infra/document-types/:", err=True)
        for problem in problems:
            typer.echo(f"  - {problem}", err=True)
        typer.echo("Run 'make pull-blueprint-schemas' and commit the result.", err=True)
        raise typer.Exit(code=1)

    typer.echo("blueprint_schemas.json matches infra/document-types/.")


if __name__ == "__main__":
    app()
