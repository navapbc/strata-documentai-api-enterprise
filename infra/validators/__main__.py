#!/usr/bin/env python3
"""Validate deployed AWS infrastructure against a committed manifest.

Why: Infrastructure is defined in Terraform but provisioned by clients who
may create resources manually (Console, CLI, scripts) rather than running
`terraform apply`. This validator answers "does the infrastructure match the intended design?" by
using tag-based discovery to find resources in AWS and checking their config
against manifest.json (a minimal, name-free spec extracted from the TF plan).
No Terraform binary or state required at runtime.

Usage:
    python -m validators [--env ENV] [--region REGION] [--bda-region REGION]
                         [--profile PROFILE] [--json] [--only CATEGORY,...]

Exit codes:
    0  - all resources present and in expected configuration
    1  - one or more resources are missing or drifted
    2  - unrecoverable error (auth failure, etc.)

Requirements:
    uv sync
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

from . import BaseValidator, Color, Result, print_report, style
from .analytics import AnalyticsValidator
from .api_gateway import ApiGatewayValidator
from .bedrock import BedrockValidator
from .cognito import CognitoValidator
from .constants import DriftStatus, Tag
from .discovery import discover_resources, extract_name_from_arn, filter_arns_by_service
from .dynamodb import DynamoDBValidator
from .ecr import EcrValidator
from .iam import IamValidator
from .lambda_ import LambdaValidator
from .logs import LogsValidator
from .monitoring import MonitoringValidator
from .s3 import S3Validator
from .sqs import SqsValidator
from .ssm import SsmValidator
from .tf import load_manifest, load_tfplan
from .triggers import TriggersValidator


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

    def __init__(
        self,
        env: str,
        region: str,
        bda_region: str,
        profile: str | None,
        *,
        project: str = "docai",
        stage: str | None = None,
        json_output: bool = False,
    ):
        self.env = env
        self.region = region
        self.bda_region = bda_region
        self.json_output = json_output
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
        self.project = project
        self.stage = stage or env
        self.service_name = f"{self.project}-{env}-{self.account_id}"
        self.ssm_prefix = f"/{self.project}/{env}"

        # Discover resources by tags
        self._log(f"  Discovering resources: project={self.project}, stage={self.stage}")
        self.component_resources = discover_resources(session, self.project, self.stage)
        discovered_count = sum(len(v) for v in self.component_resources.values())
        self._log(
            f"  Found {discovered_count} resources "
            f"across {len(self.component_resources)} components"
        )

        # Load manifest: prefer manifest.json (committed), fall back to tfplan.json
        manifest_path = Path(__file__).parent.parent / "manifest.json"
        tfplan_path = Path(__file__).parent.parent / "tfplan.json"

        if manifest_path.exists():
            self.manifest = load_manifest(manifest_path, self.account_id, env)
            self._log(f"  Loaded manifest.json ({len(self.manifest)} components)")
        elif tfplan_path.exists():
            self.manifest = load_tfplan(tfplan_path)
            self._log(f"  Loaded tfplan.json ({len(self.manifest)} components)")
        else:
            print(
                f"{style('Error', Color.RED)}: neither manifest.json nor tfplan.json found. "
                "Run 'make infra-manifest' (with TF) or commit manifest.json.",
                file=sys.stderr,
            )
            sys.exit(2)

    def _log(self, msg: str):
        """Print progress to stderr. Suppressed when --json is active."""
        if not self.json_output:
            print(msg, file=sys.stderr)

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
            self._log(f"\n{style('▸ Untagged Resources', Color.BOLD)}")
            self._log(
                f"  {style(str(len(untagged)), Color.YELLOW)} resources tagged project+stage "
                f"but missing component tag:"
            )
            for arn in sorted(untagged):
                self._log(f"    {style('?', Color.YELLOW)}  {arn}")

    def report_orphans(self):
        """Report discovered components not in the Terraform plan."""
        expected = set(self.manifest.keys())
        discovered = set(self.component_resources.keys()) - {Tag.UNTAGGED}
        orphans = discovered - expected
        if orphans:
            self._log(f"\n{style('▸ Unexpected Components (not in Terraform)', Color.BOLD)}")
            self._log(
                f"  {style(str(len(orphans)), Color.YELLOW)} components discovered but not in manifest.json:"
            )
            for component_name in sorted(orphans):
                arns = self.component_resources[component_name]
                self._log(
                    f"    {style('?', Color.YELLOW)}  component={component_name} ({len(arns)} resources)"
                )
                for arn in arns[:3]:
                    self._log(f"         {arn}")
                if len(arns) > 3:
                    self._log(f"         ... and {len(arns) - 3} more")

    def report_missing_components(self):
        """Report expected components not found via tag discovery.

        Skips components already validated by a checker (PRESENT or UNDISCOVERABLE),
        and BDA components (handled by their own direct-API validator).
        """
        expected = set(self.manifest.keys())
        discovered = set(self.component_resources.keys()) - {Tag.UNTAGGED}
        missing = expected - discovered

        if not missing:
            return

        # BDA components use direct API, not tagging - skip them here
        missing = {c for c in missing if not c.startswith("bda-")}
        if not missing:
            return

        untagged_arns = self.component_resources.get(Tag.UNTAGGED, [])

        has_output = False
        for component_name in sorted(missing):
            # If any result already references this component, skip it
            if any(
                _references_component(r.name, component_name, expected)
                for r in self.results
                if r.status in (DriftStatus.PRESENT, DriftStatus.UNDISCOVERABLE)
            ):
                continue

            # Check if any untagged ARN belongs to this component by naming convention
            matching_untagged = [
                arn for arn in untagged_arns if _references_component(arn, component_name, expected)
            ]

            if not has_output:
                self._log(
                    f"\n{style('▸ Missing Components (expected but not discovered)', Color.BOLD)}"
                )
                has_output = True

            if matching_untagged:
                self._log(
                    f"    {style('~', Color.YELLOW)}  component={component_name} (present but untagged)"
                )
            else:
                component = self.manifest[component_name]
                resource_types = [r.resource_type for r in component.resources[:3]]
                self._log(
                    f"    {style('?', Color.YELLOW)}  component={component_name} ({', '.join(resource_types)})"
                )

    def run(self, only: list[str] | None = None):
        checks = {k: v for k, v in self.ALL_CHECKS.items() if not only or k in only}
        for label, method in checks.values():
            self._log(f"\n{style(f'▸ {label}', Color.BOLD)}")
            try:
                getattr(self, method)()
            except Exception as exc:
                self._log(f"  {style('ERROR', Color.RED)} in {label}: {exc}")

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
    parser.add_argument("--project", default="docai", help="Project tag value (default: docai)")
    parser.add_argument(
        "--stage",
        default=None,
        help="Stage tag value for discovery (default: same as --env)",
    )
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
        print(
            f"  env={args.env}  stage={args.stage or args.env}"
            f"  project={args.project}  region={args.region}"
        )
        print("─" * 70)

    try:
        validator = InfraValidator(
            env=args.env,
            region=args.region,
            bda_region=args.bda_region,
            profile=args.profile,
            project=args.project,
            stage=args.stage,
            json_output=args.json,
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
