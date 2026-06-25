"""CloudWatch Logs validation."""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.discovery import extract_name_from_arn, filter_arns_by_service


class LogsValidator(BaseValidator):
    def check_log_groups(self):
        cat = "CloudWatch Logs"
        # API log group is derived from the API Gateway Lambda function name
        arns = self.component_resources.get("api-gateway", [])
        lambda_arns = filter_arns_by_service(arns, "lambda")
        if not lambda_arns:
            self.missing(cat, "Log Group", "component=api-gateway (no Lambda discovered)")
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
                self.check_or_drift(cat, "Log Group", name, drift)
            else:
                self.missing(cat, "Log Group", name)
        except ClientError as e:
            self.missing(cat, "Log Group", name, str(e))
