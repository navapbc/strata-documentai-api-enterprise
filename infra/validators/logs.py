"""CloudWatch Logs validation."""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.discovery import extract_name_from_arn, filter_arns_by_service


class LogsValidator(BaseValidator):
    category = "CloudWatch Logs"
    def check_log_groups(self):

        # API log group is derived from the API Gateway Lambda function name
        arns = self.component_resources.get("api-gateway", [])
        lambda_arns = filter_arns_by_service(arns, "lambda")

        if lambda_arns:
            api_name = extract_name_from_arn(lambda_arns[0])
        else:
            # Fall back to expected.json
            spec = self.planned_tf_resources.get("api-gateway")
            if spec:
                lmb = spec.get_by_type("aws_lambda_function")
                api_name = lmb.values.get("function_name") if lmb else None
            else:
                api_name = None

        if not api_name:
            self.missing(self.category, "Log Group", "component=api-gateway (not discovered)")
            return

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
