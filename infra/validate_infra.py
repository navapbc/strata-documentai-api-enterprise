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
import sys
from typing import ClassVar

try:
    import boto3
    from botocore.exceptions import NoCredentialsError
except ImportError:
    sys.exit("boto3 is required: pip install boto3")

from validators import BaseValidator, Result, bold, print_report, red, yellow
from validators.analytics import AnalyticsValidator
from validators.api_gateway import ApiGatewayValidator
from validators.bedrock import BedrockValidator
from validators.cognito import CognitoValidator
from validators.discovery import discover_resources, extract_name_from_arn, filter_arns_by_service
from validators.dynamodb import DynamoDBValidator
from validators.ecr import EcrValidator
from validators.iam import IamValidator
from validators.lambda_ import LambdaValidator
from validators.logs import LogsValidator
from validators.s3 import S3Validator
from validators.sqs import SqsValidator
from validators.ssm import SsmValidator

# Components that validators know how to check. Used for orphan detection -
# any discovered component not in this set is flagged as unexpected.
KNOWN_COMPONENTS: set[str] = {
    "ecr",
    "input-bucket",
    "output-bucket",
    "metrics-bucket",
    "admin-ui",
    "demo-ui",
    "document-metadata",
    "api-keys",
    "tenants",
    "audit-events",
    "extraction-rules",
    "document-categories",
    "document-batches",
    "document-builds",
    "metrics-queue",
    "api-gateway",
    "document-processor",
    "bda-result-processor",
    "metrics-processor",
    "metrics-aggregator",
    "identity-provider",
    "analytics",
    "config",
    "secrets",
}


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
        "bedrock": ("Bedrock DA", "check_bedrock"),
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
            self.lmb = session.client("lambda")
            self.sqs = session.client("sqs")
            self.apigw = session.client("apigatewayv2")
            self.cognito = session.client("cognito-idp")
            self.ssm = session.client("ssm")
            self.glue = session.client("glue")
            self.athena = session.client("athena")
            self.iam = session.client("iam")
            self.logs = session.client("logs")
            self.bda = bda_session.client("bedrock-data-automation")

        except NoCredentialsError:
            print(
                "No AWS credentials found. Configure ~/.aws/credentials or set env vars.",
                file=sys.stderr,
            )
            sys.exit(2)

        self.account_id = self.sts.get_caller_identity()["Account"]
        self.project = "docai"
        self.sn = f"{self.project}-{env}-{self.account_id}"
        self.ssm_prefix = f"/{self.project}/{env}"

        # Discover resources by tags
        print(f"  Discovering resources: project={self.project}, stage={env}")
        self.component_resources = discover_resources(session, self.project, env)
        discovered_count = sum(len(v) for v in self.component_resources.values())
        print(
            f"  Found {discovered_count} resources "
            f"across {len(self.component_resources)} components"
        )

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
        untagged = self.component_resources.get("_untagged", [])
        if untagged:
            print(f"\n{bold('▸ Untagged Resources')}")
            print(
                f"  {yellow(str(len(untagged)))} resources tagged project+stage "
                f"but missing component tag:"
            )
            for arn in sorted(untagged):
                print(f"    {yellow('?')}  {arn}")

    def report_orphans(self):
        """Report discovered components that no validator knows about."""
        known = KNOWN_COMPONENTS | {"_untagged"}
        # BDA components are dynamic (bda-*)
        discovered_components = set(self.component_resources.keys())
        orphans = {
            c for c in discovered_components
            if c not in known and not c.startswith("bda-")
        }
        if orphans:
            print(f"\n{bold('▸ Unexpected Components')}")
            print(f"  {yellow(str(len(orphans)))} components discovered but not expected:")
            for comp in sorted(orphans):
                arns = self.component_resources[comp]
                print(f"    {yellow('?')}  component={comp} ({len(arns)} resources)")
                for arn in arns[:3]:
                    print(f"         {arn}")
                if len(arns) > 3:
                    print(f"         ... and {len(arns) - 3} more")

    def run(self, only: list[str] | None = None):
        checks = {k: v for k, v in self.ALL_CHECKS.items() if not only or k in only}
        for label, method in checks.values():
            print(f"\n{bold(f'▸ {label}')}")
            try:
                getattr(self, method)()
            except Exception as exc:
                print(f"  {red('ERROR')} in {label}: {exc}")

        # Surface untagged and orphaned resources
        self.report_untagged()
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
        print(f"\n{bold('Infra Drift Validator (tag-based discovery)')}")
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
        print(f"{red('Fatal')}: {e}", file=sys.stderr)
        sys.exit(2)

    if not args.json:
        print(f"  Account : {validator.account_id}")
        print(f"  Service : {validator.sn}")
        print(f"  Checks  : {', '.join(only or list(InfraValidator.ALL_CHECKS))}")

    validator.run(only=only)
    exit_code = print_report(validator.results, args.json)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
