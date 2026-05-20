"""Generate a sunburst chart visualizing the API endpoint structure."""

import plotly.graph_objects as go  # type: ignore[import-untyped]
import typer

app = typer.Typer()


def _get_supported_file_types() -> dict[str, list[str]]:
    """Derive supported file types from FileValidation constants."""
    from documentai_api.config.constants import FileValidation

    native = [t.split("/")[1].upper() for t in FileValidation.BDA_NATIVE]
    converted = [t.split("/")[1].upper() for t in FileValidation.REQUIRES_CONVERSION]
    return {"BDA Native": native, "Converted to PNG": converted}


# Type alias for the nested endpoint tree
EndpointTree = dict[str, dict[str, dict[str, list[dict[str, str]]]]]


def _get_endpoint_tree() -> EndpointTree:
    """Pull endpoints from the FastAPI app, organized as group > subgroup > method > endpoints."""
    from fastapi.routing import APIRoute

    from documentai_api.app import app as fastapi_app

    excluded = {"/", "/health", "/config", "/openapi.json", "/docs", "/redoc"}
    tree: EndpointTree = {}

    for route in fastapi_app.routes:
        if not isinstance(route, APIRoute) or route.path in excluded:
            continue

        tag = str(route.tags[0]) if route.tags else "Other:Other"
        group, subgroup = tag.split(":", 1) if ":" in tag else (tag, "Other")

        for method in route.methods:
            tree.setdefault(group, {}).setdefault(subgroup, {}).setdefault(method, []).append(
                {
                    "path": route.path,
                    "name": route.name or "",
                }
            )

    return tree


def _build_sunburst_data() -> tuple[list[str], list[str], list[str], list[str]]:
    """Build parallel arrays for the sunburst chart."""
    ids: list[str] = []
    labels: list[str] = []
    parents: list[str] = []
    hover: list[str] = []

    def add(node_id: str, label: str, parent: str, text: str) -> None:
        ids.append(node_id)
        labels.append(label)
        parents.append(parent)
        hover.append(text)

    tree = _get_endpoint_tree()

    # root
    add("API", "DocumentAI API", "", "Document processing API")

    # endpoint tree
    for group, subgroups in tree.items():
        add(
            group,
            group,
            "API",
            f"{sum(len(eps) for methods in subgroups.values() for eps in methods.values())} endpoints",
        )

        for subgroup, methods in subgroups.items():
            subgroup_id = f"{group}/{subgroup}"
            ep_count = sum(len(eps) for eps in methods.values())
            add(subgroup_id, subgroup, group, f"{ep_count} endpoints")

            for method, endpoints in methods.items():
                method_id = f"{subgroup_id}/{method}"
                add(method_id, method, subgroup_id, f"{len(endpoints)} {method} endpoints")

                for ep in endpoints:
                    add(
                        f"{method_id}/{ep['path']}",
                        ep["name"] or ep["path"],
                        method_id,
                        f"{method} {ep['path']}",
                    )

    # file types
    supported_file_types = _get_supported_file_types()
    add(
        "FileTypes",
        "Supported Files",
        "API",
        f"{sum(len(v) for v in supported_file_types.values())} formats",
    )

    for category, types in supported_file_types.items():
        cat_id = f"FileTypes/{category}"
        add(cat_id, category, "FileTypes", ", ".join(types))

        for file_type in types:
            add(f"{cat_id}/{file_type}", file_type, cat_id, f"{file_type} format")

    return ids, labels, parents, hover


@app.command()
def generate(
    output: str = typer.Option("api_sunburst.html", help="Output file path (.html, .png, .jpg)"),
) -> None:
    """Generate API sunburst chart."""
    ids, labels, parents, hover = _build_sunburst_data()

    fig = go.Figure(
        go.Sunburst(
            ids=ids,
            labels=labels,
            parents=parents,
            hovertext=hover,
            hoverinfo="text",
            textfont=dict(size=14),
        )
    )

    fig.update_layout(
        width=900,
        height=900,
        margin=dict(t=0, l=0, r=0, b=0),
    )

    if output.endswith(".html"):
        fig.write_html(output, include_plotlyjs=True, full_html=True)
    else:
        fig.write_image(output, scale=2)

    typer.echo(f"Sunburst chart written to {output}")


if __name__ == "__main__":
    app()
