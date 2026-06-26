#!/usr/bin/env python3
"""Generate manifest.json from tfplan.json (terraform plan output).

Distills a full Terraform plan into the minimal set of attributes each
validator needs, grouped by component tag. The output is name-free and
committed - it's what clients validate against without needing Terraform.

Usage:
    python -m validators.generate [--expected PATH] [--output PATH]
"""

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

# Resource types we care about and the attributes to extract from their values.
EXTRACTORS: dict[str, Callable] = {}


def extractor(resource_type: str):
    """Register an attribute extractor for a resource type."""

    def decorator(fn):
        EXTRACTORS[resource_type] = fn
        return fn

    return decorator


@extractor("aws_dynamodb_table")
def _ddb(values: dict) -> dict:
    entry = {"type": "aws_dynamodb_table", "hash_key": values.get("hash_key")}
    if values.get("range_key"):
        entry["range_key"] = values["range_key"]
    gsis = values.get("global_secondary_index") or []
    if gsis:
        entry["gsi_names"] = sorted(g["name"] for g in gsis if g.get("name"))
    ttl = values.get("ttl") or []
    if ttl and ttl[0].get("enabled"):
        entry["ttl_attribute"] = ttl[0].get("attribute_name")
    return entry


@extractor("aws_lambda_function")
def _lambda(values: dict) -> dict:
    return {
        "type": "aws_lambda_function",
        "memory_size": values.get("memory_size", 512),
        "timeout": values.get("timeout", 300),
    }


@extractor("aws_s3_bucket")
def _s3(values: dict) -> dict:
    return {"type": "aws_s3_bucket"}


@extractor("aws_sqs_queue")
def _sqs(values: dict) -> dict:
    return {"type": "aws_sqs_queue"}


@extractor("aws_apigatewayv2_api")
def _apigw(values: dict) -> dict:
    return {"type": "aws_apigatewayv2_api", "protocol_type": values.get("protocol_type")}


@extractor("aws_cloudwatch_log_group")
def _log_group(values: dict) -> dict:
    entry = {"type": "aws_cloudwatch_log_group"}
    if values.get("retention_in_days"):
        entry["retention_in_days"] = values["retention_in_days"]
    return entry


@extractor("aws_cognito_user_pool")
def _cognito(values: dict) -> dict:
    return {"type": "aws_cognito_user_pool"}


@extractor("aws_ssm_parameter")
def _ssm(values: dict) -> dict:
    entry = {"type": "aws_ssm_parameter"}
    if values.get("type"):
        entry["parameter_type"] = values["type"]
    return entry


@extractor("aws_athena_workgroup")
def _athena(values: dict) -> dict:
    return {"type": "aws_athena_workgroup"}


@extractor("aws_glue_catalog_database")
def _glue_db(values: dict) -> dict:
    return {"type": "aws_glue_catalog_database"}


@extractor("aws_ecr_repository")
def _ecr(values: dict) -> dict:
    return {"type": "aws_ecr_repository"}


@extractor("awscc_bedrock_data_automation_project")
def _bda_project(values: dict) -> dict:
    return {"type": "awscc_bedrock_data_automation_project"}


@extractor("aws_sns_topic")
def _sns(values: dict) -> dict:
    return {"type": "aws_sns_topic"}


@extractor("aws_cloudwatch_event_rule")
def _event_rule(values: dict) -> dict:
    return {"type": "aws_cloudwatch_event_rule"}


@extractor("aws_lambda_event_source_mapping")
def _esm(values: dict) -> dict:
    return {"type": "aws_lambda_event_source_mapping"}


def extract_component_tag(resource: dict) -> str | None:
    """Get component tag from a resource's values."""
    values = resource.get("values", {})
    tags = values.get("tags") or values.get("tags_all") or {}
    if isinstance(tags, list):
        tags = {t["key"]: t["value"] for t in tags if "key" in t and "value" in t}
    return tags.get("component")


def process_plan(data: dict) -> dict[str, list[dict]]:
    """Walk terraform plan and extract manifest entries grouped by component."""
    components: dict[str, list[dict]] = defaultdict(list)

    def process_resource(resource: dict):
        rtype = resource.get("type", "")
        if rtype not in EXTRACTORS:
            return

        component = extract_component_tag(resource)
        if not component:
            return

        values = resource.get("values", {})
        entry = EXTRACTORS[rtype](values)

        components[component].append(entry)

    def walk(module: dict):
        for r in module.get("resources", []):
            if r.get("mode") == "managed":
                process_resource(r)
        for child in module.get("child_modules", []):
            walk(child)

    root = data.get("planned_values", {}).get("root_module", {})
    for r in root.get("resources", []):
        if r.get("mode") == "managed":
            process_resource(r)
    walk(root)

    return dict(components)


def dedupe_entries(entries: list[dict]) -> list[dict]:
    """Collapse identical entries, adding count when > 1."""
    counts: dict[str, int] = {}
    unique: dict[str, dict] = {}
    for e in entries:
        key = json.dumps(e, sort_keys=True)
        counts[key] = counts.get(key, 0) + 1
        unique[key] = e

    result = []
    for key, entry in unique.items():
        if counts[key] > 1:
            entry = {**entry, "count": counts[key]}
        result.append(entry)
    return result


def main():
    parser = argparse.ArgumentParser(description="Generate manifest.json from terraform plan.")
    parser.add_argument("--expected", default="tfplan.json", help="Path to tfplan.json")
    parser.add_argument("--output", default="manifest.json", help="Output path for manifest.json")
    args = parser.parse_args()

    expected_path = Path(args.expected)
    if not expected_path.exists():
        sys.exit(f"Error: {expected_path} not found. Run 'make infra-expected' first.")

    data = json.loads(expected_path.read_text())
    components = process_plan(data)

    output = {}
    for component in sorted(components):
        output[component] = dedupe_entries(components[component])

    output_path = Path(args.output)
    output_path.write_text(json.dumps(output, indent=2) + "\n")

    total = sum(len(v) for v in output.values())
    print(f"Generated {output_path}: {len(output)} components, {total} resources")


if __name__ == "__main__":
    main()
