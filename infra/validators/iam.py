"""IAM policy and role validation.

IAM roles are derived from Lambda function names (function-name + "-role").
"""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.constants import AwsErrorCode
from validators.discovery import extract_name_from_arn, filter_arns_by_service


class IamValidator(BaseValidator):
    category = "IAM"
    def check_iam(self):

        # Find all components that have Lambda functions
        for component_name, spec in sorted(self.planned_tf_resources.items()):
            lmb = spec.get_by_type("aws_lambda_function")
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
            try:
                self.iam.get_role(RoleName=role_name)
                self.ok(self.category, "IAM Role", role_name)
            except ClientError as e:
                code = e.response["Error"]["Code"]
                if code == AwsErrorCode.NO_SUCH_ENTITY:
                    self.missing(self.category, "IAM Role", role_name)
                else:
                    self.missing(self.category, "IAM Role", role_name, str(e))
