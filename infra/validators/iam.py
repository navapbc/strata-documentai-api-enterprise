"""IAM policy and role validation.

Note: IAM resources are global and the Resource Groups Tagging API coverage
for IAM is limited. This validator still uses convention-based name lookup
for roles and policies, as these are derived from the Lambda function names
which we discover via tags.
"""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.constants import AwsErrorCode
from validators.discovery import extract_name_from_arn, filter_arns_by_service


class IamValidator(BaseValidator):
    def check_iam(self):
        cat = "IAM"

        # IAM roles - derived from discovered Lambda function names
        lambda_components = [
            "api-gateway",
            "document-processor",
            "bda-result-processor",
            "metrics-processor",
            "metrics-aggregator",
        ]
        for component_tag in lambda_components:
            arns = self.component_resources.get(component_tag, [])
            lambda_arns = filter_arns_by_service(arns, "lambda")
            if not lambda_arns:
                continue
            name = extract_name_from_arn(lambda_arns[0])
            role_name = f"{name}-role"
            try:
                self.iam.get_role(RoleName=role_name)
                self.ok(cat, "IAM Role", role_name)
            except ClientError as e:
                code = e.response["Error"]["Code"]
                if code == AwsErrorCode.NO_SUCH_ENTITY:
                    self.missing(cat, "IAM Role", role_name)
                else:
                    self.missing(cat, "IAM Role", role_name, str(e))
