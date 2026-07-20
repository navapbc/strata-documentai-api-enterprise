"""CLI to write blueprint field label files.

Fetches blueprints from BDA project(s) and writes field label JSON files
into config/field_labels/. Merges new fields without overwriting existing labels.
"""

import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from documentai_api.utils.field_labels import _to_human_label

app = typer.Typer()

LABELS_DIR = Path(__file__).resolve().parent.parent / "config" / "field_labels"


class BlueprintFilter(StrEnum):
    MANAGED = "managed"
    CUSTOM = "custom"
    ALL = "all"


def _is_managed(bp_arn: str) -> bool:
    return ":aws:blueprint/" in bp_arn


@app.command()
def write(
    project_arn: Annotated[
        list[str] | None,
        typer.Option(help="One or more BDA project ARNs. If omitted, reads BDA_PROJECT_ARNS env."),
    ] = None,
    filter: Annotated[
        BlueprintFilter,
        typer.Option(help="Filter blueprints: managed, custom, or all."),
    ] = BlueprintFilter.ALL,
) -> None:
    """Write field label files, merging new fields without overwriting existing labels."""
    import os

    from documentai_api.services.bda import get_blueprint, get_data_automation_project
    from documentai_api.utils.schemas import _extract_fields

    arns: dict[str, str] = {}

    if project_arn:
        for i, arn in enumerate(project_arn):
            arns[f"arg-{i}"] = arn
    else:
        project_arns_json = os.environ.get("BDA_PROJECT_ARNS")
        if project_arns_json:
            arns = json.loads(project_arns_json)
        else:
            single = os.environ.get("BDA_PROJECT_ARN_ALL")
            if single:
                arns = {"default": single}
            else:
                typer.echo("Error: No project ARN provided and BDA_PROJECT_ARNS not set.", err=True)
                raise typer.Exit(code=1)

    LABELS_DIR.mkdir(parents=True, exist_ok=True)

    for category, arn in arns.items():
        typer.echo(f"Fetching project: {category} ({arn})")
        try:
            project = get_data_automation_project(arn)
            blueprints = (
                project.get("project", {})
                .get("customOutputConfiguration", {})
                .get("blueprints", [])
            )

            for bp_config in blueprints:
                bp_arn = bp_config.get("blueprintArn")
                if not bp_arn:
                    continue

                bp_response = get_blueprint(bp_arn)
                bp = bp_response.get("blueprint", {})

                managed = _is_managed(bp.get("blueprintArn", ""))
                if filter == BlueprintFilter.MANAGED and not managed:
                    continue
                if filter == BlueprintFilter.CUSTOM and managed:
                    continue

                schema = json.loads(bp.get("schema", "{}"))
                doc_type = schema.get("class", bp.get("blueprintName", "Unknown"))
                label_file = LABELS_DIR / f"{doc_type.lower()}.json"

                # Load existing labels
                existing: dict[str, str] = {}
                if label_file.exists():
                    existing = json.loads(label_file.read_text())

                # Merge - only add fields not already present
                fields = _extract_fields(schema)
                added = 0
                for field in fields:
                    name = field["name"]
                    if name not in existing:
                        existing[name] = _to_human_label(name)
                        added += 1

                label_file.write_text(json.dumps(existing, indent=2) + "\n")

                if added:
                    typer.echo(f"  {doc_type}: added {added} new field(s)")
                else:
                    typer.echo(f"  {doc_type}: up to date")

        except Exception as e:
            typer.echo(f"  Error on {category}: {e}")

    typer.echo("\nDone.")


if __name__ == "__main__":
    app()
