"""SSM Parameter Store validation."""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.constants import AwsErrorCode
from validators.discovery import filter_arns_by_service


class SsmValidator(BaseValidator):
    def check_ssm(self):
        cat = "SSM"

        # Config parameters (String type)
        config_arns = self.component_resources.get("config", [])
        config_params = [
            arn.split(":parameter")[-1]
            for arn in filter_arns_by_service(config_arns, "ssm")
        ]

        if not config_params:
            self.missing(cat, "SSM Parameter", "component=config (not discovered)")
        else:
            for param in config_params:
                try:
                    p = self.ssm.get_parameter(Name=param)["Parameter"]
                    drift = []
                    if p["Type"] != "String":
                        drift.append(f"type: expected String, got {p['Type']}")
                    self.check_or_drift(cat, "SSM Parameter", param, drift)
                except ClientError as e:
                    code = e.response["Error"]["Code"]
                    if code == AwsErrorCode.PARAMETER_NOT_FOUND:
                        self.missing(cat, "SSM Parameter", param)
                    else:
                        self.missing(cat, "SSM Parameter", param, str(e))

        # Secret parameters (SecureString type)
        secret_arns = self.component_resources.get("secrets", [])
        secret_params = [
            arn.split(":parameter")[-1]
            for arn in filter_arns_by_service(secret_arns, "ssm")
        ]

        if not secret_params:
            self.missing(cat, "SSM Parameter (SecureString)", "component=secrets (not discovered)")
        else:
            for param in secret_params:
                try:
                    p = self.ssm.get_parameter(Name=param, WithDecryption=False)["Parameter"]
                    drift = []
                    if p["Type"] != "SecureString":
                        drift.append(f"type: expected SecureString, got {p['Type']}")
                    self.check_or_drift(cat, "SSM Parameter (SecureString)", param, drift)
                except ClientError as e:
                    code = e.response["Error"]["Code"]
                    if code == AwsErrorCode.PARAMETER_NOT_FOUND:
                        self.missing(cat, "SSM Parameter (SecureString)", param)
                    else:
                        self.missing(cat, "SSM Parameter (SecureString)", param, str(e))
