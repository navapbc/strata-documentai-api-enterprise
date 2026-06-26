"""IAM role and policy attachment validation.

Checks that each Lambda role exists AND that its attached policies match
exactly what Terraform declares - no unauthorized additions, no missing
attachments.

Roles are derived from Lambda function names (function-name + "-role")
since IAM roles don't carry the component tag.
"""

from botocore.exceptions import ClientError

from . import BaseValidator
from .constants import AwsErrorCode
from .discovery import extract_name_from_arn, filter_arns_by_service

# AWS-managed policies that every Lambda role gets
AWS_MANAGED_POLICIES = {
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
}


class IamValidator(BaseValidator):
    category = "IAM"

    def _expected_policy_arns(self) -> set[str]:
        """The custom policy ARNs all Lambda roles should have attached.

        These 4 suffixes mirror local.lambda_policy_arns in
        environments/dev/main.tf. They can't be derived from tfplan.json
        because policy ARNs are known-after-apply and locals aren't emitted
        in terraform show -json. If lambda_policy_arns changes in TF, update
        the suffixes here.

        NOTE: if VPC is enabled (prd), AWSLambdaVPCAccessExecutionRole will
        also be attached - add it to AWS_MANAGED_POLICIES for that env.
        """
        return AWS_MANAGED_POLICIES | {
            f"arn:aws:iam::{self.account_id}:policy/{self.service_name}-{suffix}"
            for suffix in ("data-access", "storage-access", "bedrock-access", "supporting-services")
        }

    def _check_role_attachments(self, role_name: str, expected_arns: set[str]):
        """Verify attached policies match expected set exactly."""
        try:
            paginator = self.iam.get_paginator("list_attached_role_policies")
            actual_arns = set()
            for page in paginator.paginate(RoleName=role_name):
                for policy in page["AttachedPolicies"]:
                    actual_arns.add(policy["PolicyArn"])
        except ClientError as e:
            self.drifted(
                self.category,
                "IAM Role Policies",
                role_name,
                [f"cannot list attached policies: {e.response['Error']['Code']}"],
            )
            return

        drift = [
            f"unexpected policy attached: {arn.rsplit('/', 1)[-1]}"
            for arn in sorted(actual_arns - expected_arns)
        ] + [
            f"expected policy not attached: {arn.rsplit('/', 1)[-1]}"
            for arn in sorted(expected_arns - actual_arns)
        ]

        self.check_or_drift(self.category, "IAM Role Policies", role_name, drift)

    def check_iam(self):
        expected_arns = self._expected_policy_arns()

        for component_name, component in sorted(self.manifest.items()):
            lmb = component.get_by_type("aws_lambda_function")
            if not lmb:
                continue

            # Get Lambda name from discovery or spec
            arns = self.component_resources.get(component_name, [])
            lambda_arns = filter_arns_by_service(arns, "lambda")
            if lambda_arns:
                name = extract_name_from_arn(lambda_arns[0])
            else:
                name = lmb.values.get("function_name")

            if not name:
                continue

            role_name = f"{name}-role"

            # Check role exists
            try:
                self.iam.get_role(RoleName=role_name)
                self.ok(self.category, "IAM Role", role_name)
            except ClientError as e:
                code = e.response["Error"]["Code"]
                if code == AwsErrorCode.NO_SUCH_ENTITY:
                    self.missing(self.category, "IAM Role", role_name)
                else:
                    self.missing(self.category, "IAM Role", role_name, str(e))
                continue

            # Check policy attachments
            self._check_role_attachments(role_name, expected_arns)
