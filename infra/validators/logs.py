"""CloudWatch Logs validation."""

from botocore.exceptions import ClientError

from . import BaseValidator
from .discovery import extract_name_from_arn, filter_arns_by_service


class LogsValidator(BaseValidator):
    category = "CloudWatch Logs"

    def check_log_groups(self):

        # API log group is derived from the API Gateway Lambda function name
        arns = self.component_resources.get("api-gateway", [])
        lambda_arns = filter_arns_by_service(arns, "lambda")

        if not lambda_arns:
            self.warn(
                self.category, "Log Group", "component=api-gateway", "not discovered via tags"
            )
            return

        api_name = extract_name_from_arn(lambda_arns[0])
        name = f"/aws/apigateway/{api_name}"
        try:
            resp = self.logs.describe_log_groups(logGroupNamePrefix=name)
            groups = [g for g in resp["logGroups"] if g["logGroupName"] == name]
            if groups:
                drift = []
                retention = groups[0].get("retentionInDays")
                if retention != 30:
                    drift.append(f"retention_in_days: expected 30, got {retention}")
                self.check_or_drift(self.category, "Log Group", name, drift)
            else:
                self.missing(self.category, "Log Group", name)
        except ClientError as e:
            self.missing(self.category, "Log Group", name, str(e))
