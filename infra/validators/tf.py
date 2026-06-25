"""Load and flatten expected.json (Terraform plan output) into a resource spec.

The spec is keyed by component tag value and contains the planned resource
configurations that validators can compare against live AWS state.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExpectedResource:
    """A single resource from the Terraform plan."""

    resource_type: str  # e.g. aws_dynamodb_table, aws_s3_bucket
    name: str  # resource name/identifier
    module: str  # module address (e.g. module.document_metadata)
    values: dict  # full planned values


@dataclass
class ComponentSpec:
    """All expected resources for a single component."""

    component: str
    resources: list[ExpectedResource] = field(default_factory=list)

    def get_by_type(self, resource_type: str) -> ExpectedResource | None:
        """Get the first resource matching a type (e.g. aws_dynamodb_table)."""
        return next((r for r in self.resources if r.resource_type == resource_type), None)

    def get_all_by_type(self, resource_type: str) -> list[ExpectedResource]:
        """Get all resources matching a type."""
        return [r for r in self.resources if r.resource_type == resource_type]


def load_expected(path: str | Path = "expected.json") -> dict[str, ComponentSpec]:
    """Load expected.json and return specs keyed by component tag.

    Walks the planned_values tree, extracts the component tag from each resource,
    and groups resources by component.
    """
    path = Path(path)
    if not path.exists():
        return {}

    data = json.loads(path.read_text())
    planned = data.get("planned_values", {}).get("root_module", {})

    specs: dict[str, ComponentSpec] = {}

    def process_resources(resources: list[dict], module_address: str):
        for r in resources:
            values = r.get("values", {})
            tags = values.get("tags") or values.get("tags_all") or {}

            # Handle awscc-style tags: [{"key": "k", "value": "v"}, ...]
            if isinstance(tags, list):
                tags = {t["key"]: t["value"] for t in tags if "key" in t and "value" in t}

            component = tags.get("component")
            if not component:
                continue

            resource = ExpectedResource(
                resource_type=r.get("type", ""),
                name=r.get("name", ""),
                module=module_address,
                values=values,
            )

            if component not in specs:
                specs[component] = ComponentSpec(component=component)
            specs[component].resources.append(resource)

    # Process root-level resources
    process_resources(planned.get("resources", []), "root")

    # Process child modules (recursively handles nested modules)
    def walk_modules(modules: list[dict]):
        for module in modules:
            address = module.get("address", "")
            process_resources(module.get("resources", []), address)
            # Recurse into nested child modules
            walk_modules(module.get("child_modules", []))

    walk_modules(planned.get("child_modules", []))

    return specs
