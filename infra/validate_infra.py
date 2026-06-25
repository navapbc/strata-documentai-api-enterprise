#!/usr/bin/env python3
"""Validate deployed AWS infrastructure against expected state using tag-based discovery.

Discovers resources by project + stage tags, then validates configuration drift
on each discovered component.

Usage:
    python validate_infra.py [--env ENV] [--region REGION] [--bda-region REGION]
                             [--profile PROFILE] [--json] [--only CATEGORY,...]

Exit codes:
    0  - all resources present and in expected configuration
    1  - one or more resources are missing or drifted
    2  - unrecoverable error (auth failure, etc.)

Requirements:
    pip install boto3
"""

import argparse
import re
import sys
from pathlib import Path
from typing import ClassVar

try:
    import boto3
    from botocore.exceptions import NoCredentialsError
except ImportError:
    sys.exit("boto3 is required: pip install boto3")

from validators import BaseValidator, Color, Result, print_report, style
from validators.analytics import AnalyticsValidator
from validators.api_gateway import ApiGatewayValidator
from validators.bedrock import BedrockValidator
from validators.cognito import CognitoValidator
from validators.constants import DriftStatus, Tag
from validators.discovery import discover_resources, extract_name_from_arn, filter_arns_by_service
from validators.dynamodb import DynamoDBValidator
from validators.ecr import EcrValidator
from validators.iam import IamValidator
from validators.lambda_ import LambdaValidator
from validators.logs import LogsValidator
from validators.monitoring import MonitoringValidator
from validators.s3 import S3Validator
from validators.sqs import SqsValidator
from validators.ssm import SsmValidator
from validators.tf import load_expected
from validators.triggers import TriggersValidator


def _component_boundary_pattern(component_name: str) -> re.Pattern:
    """Create a regex that matches component_name delimited by non-name chars.

    Matches when component_name appears bounded by non-alphanumeric chars (or
    start/end of string). NOTE: because component names are hyphen-delimited,
    this alone does NOT stop 'metrics' from matching 'metrics-aggregator' (the
    hyphen counts as a boundary) - use _references_component for that.
    """
    escaped = re.escape(component_name)
    return re.compile(rf"(?:^|[^a-zA-Z0-9]){escaped}(?:$|[^a-zA-Z0-9])")


def _references_component(name: str, component_name: str, all_components: set[str]) -> bool:
    """True if `name` refers to `component_name` as a maximal component token.

    Boundary-matches `component_name`, then rejects the match if a longer
    expected component that contains it also matches `name`. This is what
    actually prevents 'metrics' from claiming a resource that belongs to
    'metrics-aggregator': both boundary-match, but the longer, more specific
    component wins.
    """
    if not _component_boundary_pattern(component_name).search(name):
        return False
    return not any(
        other != component_name
        and component_name in other
        and _component_boundary_pattern(other).search(name)
        for other in all_components
    )


class InfraValidator(
    EcrValidator,
    S3Validator,
    DynamoDBValidator,
    LambdaValidator,
    SqsValidator,
    ApiGatewayValidator,
    LogsValidator,
    CognitoValidator,
    SsmValidator,
    AnalyticsValidator,
    IamValidator,
    BedrockValidator,
    MonitoringValidator,
    TriggersValidator,
    BaseValidator,
):
    """Composed validator using tag-based resource discovery."""

    ALL_CHECKS: ClassVar[dict[str, tuple[str, str]]] = {
        "ecr": ("ECR", "check_ecr"),
        "s3": ("S3", "check_s3"),
        "dynamodb": ("DynamoDB", "check_dynamodb"),
        "lambda": ("Lambda", "check_lambdas"),
        "sqs": ("SQS", "check_sqs"),
        "api-gateway": ("API Gateway", "check_api_gateway"),
        "logs": ("CloudWatch Logs", "check_log_groups"),
        "cognito": ("Cognito", "check_cognito"),
        "ssm": ("SSM", "check_ssm"),
        "analytics": ("Glue / Athena", "check_analytics"),
        "iam": ("IAM", "check_iam"),
        "bedrock": ("Bedrock Data Automation", "check_bedrock"),
        "monitoring": ("Monitoring", "check_monitoring"),
        "triggers": ("Triggers", "check_triggers"),
    }

    def __init__(self, env: str, region: str, bda_region: str, profile: str | None):
        self.env = env
        self.region = region
        self.bda_region = bda_region
        self.results: list[Result] = []

        try:
            session = boto3.Session(profile_name=profile, region_name=region)
            bda_session = boto3.Session(profile_name=profile, region_name=bda_region)

            self.sts = session.client("sts")
            self.s3 = session.client("s3")
            self.ddb = session.client("dynamodb")
            self.ecr = session.client("ecr")
            self.lambda_client = session.client("lambda")
            self.sqs = session.client("sqs")
            self.apigw = session.client("apigatewayv2")
            self.cognito = session.client("cognito-idp")
            self.ssm = session.client("ssm")
            self.glue = session.client("glue")
            self.athena = session.client("athena")
            self.iam = session.client("iam")
            self.logs = session.client("logs")
            self.events = session.client("events")
            self.cloudwatch = session.client("cloudwatch")
            self.bda = bda_session.client("bedrock-data-automation")

        except NoCredentialsError:
            print(
                "No AWS credentials found. Configure ~/.aws/credentials or set env vars.",
                file=sys.stderr,
            )
            sys.exit(2)

        self.account_id = self.sts.get_caller_identity()["Account"]
        self.project = "docai"
        self.service_name = f"{self.project}-{env}-{self.account_id}"
        self.ssm_prefix = f"/{self.project}/{env}"

        # Discover resources by tags
        print(f"  Discovering resources: project={self.project}, stage={env}")
        self.component_resources = discover_resources(session, self.project, env)
        discovered_count = sum(len(v) for v in self.component_resources.values())
        print(
            f"  Found {discovered_count} resources "
            f"across {len(self.component_resources)} components"
        )

        # Load expected spec from Terraform plan
        expected_path = Path(__file__).parent / "expected.json"
        self.planned_tf_resources = load_expected(expected_path)
        if not self.planned_tf_resources:
            print(
                f"{style('Error', Color.RED)}: expected.json not found. "
                "Run 'make infra-expected' to generate it.",
                file=sys.stderr,
            )
            sys.exit(2)
        print(f"  Loaded expected.json ({len(self.planned_tf_resources)} components)")

    def get_resource_name_by_component_tag(self, component_tag: str) -> str | None:
        """Get the resource name for a component tag value from discovered resources."""
        arns = self.component_resources.get(component_tag, [])
        if not arns:
            return None
        return extract_name_from_arn(arns[0])

    def get_resource_names_by_component_tag(
        self, component_tag: str, service: str | None = None
    ) -> list[str]:
        """Get all resource names for a component tag value, optionally filtered by service."""
        arns = self.component_resources.get(component_tag, [])
        if service:
            arns = filter_arns_by_service(arns, service)
        return [extract_name_from_arn(arn) for arn in arns]

    def report_untagged(self):
        """Report resources that were discovered but missing a component tag."""
        untagged = self.component_resources.get(Tag.UNTAGGED, [])
        if untagged:
            print(f"\n{style('▸ Untagged Resources', Color.BOLD)}")
            print(
                f"  {style(str(len(untagged)), Color.YELLOW)} resources tagged project+stage "
                f"but missing component tag:"
            )
            for arn in sorted(untagged):
                print(f"    {style('?', Color.YELLOW)}  {arn}")

    def report_orphans(self):
        """Report discovered components not in the Terraform plan."""
        expected = set(self.planned_tf_resources.keys())
        discovered = set(self.component_resources.keys()) - {Tag.UNTAGGED}
        orphans = discovered - expected
        if orphans:
            print(f"\n{style('▸ Unexpected Components (not in Terraform)', Color.BOLD)}")
            print(f"  {style(str(len(orphans)), Color.YELLOW)} components discovered but not in expected.json:")
            for component_name in sorted(orphans):
                arns = self.component_resources[component_name]
                print(f"    {style('?', Color.YELLOW)}  component={component_name} ({len(arns)} resources)")
                for arn in arns[:3]:
                    print(f"         {arn}")
                if len(arns) > 3:
                    print(f"         ... and {len(arns) - 3} more")

    def report_missing_components(self):
        """Report expected components not found via tag discovery.

        Skips components already validated as PRESENT by a checker, and
        cross-references untagged ARNs before declaring truly missing.
        """
        expected = set(self.planned_tf_resources.keys())
        discovered = set(self.component_resources.keys()) - {Tag.UNTAGGED}
        missing = expected - discovered

        if not missing:
            return

        untagged_arns = self.component_resources.get(Tag.UNTAGGED, [])

        has_output = False
        for component_name in sorted(missing):
            # If any PRESENT result references this component, skip it
            if any(
                _references_component(r.name, component_name, expected)
                for r in self.results
                if r.status == DriftStatus.PRESENT
            ):
                continue

            spec = self.planned_tf_resources[component_name]

            # Check if any untagged ARN belongs to this component by naming convention
            matching_untagged = [
                arn for arn in untagged_arns
                if _references_component(arn, component_name, expected)
            ]

            if not has_output:
                print(f"\n{style('▸ Missing Components (expected but not discovered)', Color.BOLD)}")
                has_output = True

            if matching_untagged:
                print(f"    {style('~', Color.YELLOW)}  component={component_name} (present but untagged)")
            else:
                resource_types = [r.resource_type for r in spec.resources[:3]]
                self.missing(
                    "Component",
                    "Terraform Component",
                    component_name,
                    f"not discovered via tags; expected: {', '.join(resource_types)}",
                )
                print(f"    {style('✗', Color.RED)}  component={component_name}")
                for r in spec.resources[:3]:
                    name = r.values.get("name", r.values.get("function_name", "?"))
                    print(f"         {r.resource_type}: {name}")

    def run(self, only: list[str] | None = None):
        checks = {k: v for k, v in self.ALL_CHECKS.items() if not only or k in only}
        for label, method in checks.values():
            print(f"\n{style(f'▸ {label}', Color.BOLD)}")
            try:
                getattr(self, method)()
            except Exception as exc:
                print(f"  {style('ERROR', Color.RED)} in {label}: {exc}")

        # Surface gaps in both directions
        self.report_untagged()
        self.report_missing_components()
        self.report_orphans()


def main():
    parser = argparse.ArgumentParser(
        description="Validate deployed AWS infrastructure using tag-based resource discovery.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Available categories: {', '.join(InfraValidator.ALL_CHECKS)}",
    )
    parser.add_argument("--env", default="dev", help="Environment/stage (default: dev)")
    parser.add_argument(
        "--region", default="us-east-1", help="Primary AWS region (default: us-east-1)"
    )
    parser.add_argument(
        "--bda-region", default="us-east-1", help="Bedrock DA region (default: us-east-1)"
    )
    parser.add_argument("--profile", default=None, help="AWS CLI profile name")
    parser.add_argument("--json", action="store_true", help="Emit results as JSON (for CI/piping)")
    parser.add_argument(
        "--only",
        default=None,
        help="Comma-separated list of categories to check (e.g. --only s3,dynamodb,lambda)",
    )
    args = parser.parse_args()

    only = [x.strip() for x in args.only.split(",")] if args.only else None
    if only:
        unknown = [c for c in only if c not in InfraValidator.ALL_CHECKS]
        if unknown:
            parser.error(
                f"Unknown categories: {', '.join(unknown)}. "
                f"Valid: {', '.join(InfraValidator.ALL_CHECKS)}"
            )

    if not args.json:
        print(f"\n{style('Infra Drift Validator', Color.BOLD)}")
        print(f"  env={args.env}  region={args.region}  bda-region={args.bda_region}")
        print("─" * 70)

    try:
        validator = InfraValidator(
            env=args.env,
            region=args.region,
            bda_region=args.bda_region,
            profile=args.profile,
        )
    except SystemExit:
        raise
    except Exception as e:
        print(f"{style('Fatal', Color.RED)}: {e}", file=sys.stderr)
        sys.exit(2)

    if not args.json:
        print(f"  Account : {validator.account_id}")
        print(f"  Service : {validator.service_name}")
        print(f"  Checks  : {', '.join(only or list(InfraValidator.ALL_CHECKS))}")

    validator.run(only=only)
    exit_code = print_report(validator.results, args.json)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
