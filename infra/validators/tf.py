"""Load infrastructure manifest into a resource model for validators.

Supports two formats:
1. manifest.json (curated, committed) - name-agnostic, tag-based resource manifest
2. tfplan.json (generated from terraform plan) - full plan output, gitignored

manifest.json is preferred. tfplan.json is used as fallback or to regenerate manifest.json.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExpectedResource:
    """A single expected resource."""

    resource_type: str
    name: str
    module: str
    values: dict


@dataclass
class ComponentManifest:
    """All expected resources for a single component."""

    component: str
    resources: list[ExpectedResource] = field(default_factory=list)

    def get_by_type(self, resource_type: str) -> ExpectedResource | None:
        """Get the first resource matching a type."""
        return next((r for r in self.resources if r.resource_type == resource_type), None)

    def get_all_by_type(self, resource_type: str) -> list[ExpectedResource]:
        """Get all resources matching a type."""
        return [r for r in self.resources if r.resource_type == resource_type]


def load_manifest(path: str | Path, account_id: str, env: str) -> dict[str, ComponentManifest]:
    """Load manifest.json (name-agnostic, tag-based resource manifest).

    account_id and env are accepted for interface compatibility but manifest.json
    no longer contains templates - resources are identified by tags, not names.
    """
    path = Path(path)
    if not path.exists():
        return {}

    data = json.loads(path.read_text())
    result: dict[str, ComponentManifest] = {}

    for component_name, resources in data.items():
        manifest = ComponentManifest(component=component_name)
        for r in resources:
            manifest.resources.append(
                ExpectedResource(
                    resource_type=r["type"],
                    name="",
                    module="",
                    values=r,
                )
            )
        result[component_name] = manifest

    return result


def load_tfplan(path: str | Path) -> dict[str, ComponentManifest]:
    """Load tfplan.json (full Terraform plan output).

    Walks the planned_values tree, extracts the component tag from each resource,
    and groups resources by component.
    """
    path = Path(path)
    if not path.exists():
        return {}

    data = json.loads(path.read_text())
    planned = data.get("planned_values", {}).get("root_module", {})

    result: dict[str, ComponentManifest] = {}

    def process_resources(resources: list[dict], module_address: str):
        for r in resources:
            values = r.get("values", {})
            tags = values.get("tags") or values.get("tags_all") or {}

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

            if component not in result:
                result[component] = ComponentManifest(component=component)
            result[component].resources.append(resource)

    process_resources(planned.get("resources", []), "root")

    def walk_modules(modules: list[dict]):
        for module in modules:
            address = module.get("address", "")
            process_resources(module.get("resources", []), address)
            walk_modules(module.get("child_modules", []))

    walk_modules(planned.get("child_modules", []))

    return result
