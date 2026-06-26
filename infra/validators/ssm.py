"""SSM Parameter Store validation."""

from botocore.exceptions import ClientError

from . import BaseValidator
from .constants import AwsErrorCode
from .discovery import filter_arns_by_service


class SsmValidator(BaseValidator):
    category = "SSM"

    def check_ssm(self):
        # Config parameters (String type)
        config_manifest = self.manifest.get("config")
        config_arns = self.component_resources.get("config", [])
        config_ssm_arns = filter_arns_by_service(config_arns, "ssm")

        if not config_ssm_arns:
            self.warn(self.category, "SSM Parameter", "component=config", "not discovered via tags")
        else:
            if config_manifest:
                expected_count = sum(
                    r.values.get("count", 1)
                    for r in config_manifest.get_all_by_type("aws_ssm_parameter")
                )
                if len(config_ssm_arns) < expected_count:
                    self.drifted(
                        self.category,
                        "SSM Parameter",
                        "component=config",
                        [f"count: expected {expected_count}, found {len(config_ssm_arns)}"],
                    )

            for arn in config_ssm_arns:
                param = arn.split(":parameter")[-1]
                try:
                    p = self.ssm.get_parameter(Name=param)["Parameter"]
                    drift = []
                    if p["Type"] != "String":
                        drift.append(f"type: expected String, got {p['Type']}")
                    self.check_or_drift(self.category, "SSM Parameter", param, drift)
                except ClientError as e:
                    code = e.response["Error"]["Code"]
                    if code == AwsErrorCode.PARAMETER_NOT_FOUND:
                        self.missing(self.category, "SSM Parameter", param)
                    else:
                        self.missing(self.category, "SSM Parameter", param, str(e))

        # Secret parameters (SecureString type)
        secret_arns = self.component_resources.get("secrets", [])
        secret_ssm_arns = filter_arns_by_service(secret_arns, "ssm")

        if not secret_ssm_arns:
            self.warn(
                self.category,
                "SSM Parameter (SecureString)",
                "component=secrets",
                "not discovered via tags",
            )
        else:
            for arn in secret_ssm_arns:
                param = arn.split(":parameter")[-1]
                try:
                    p = self.ssm.get_parameter(Name=param, WithDecryption=False)["Parameter"]
                    drift = []
                    if p["Type"] != "SecureString":
                        drift.append(f"type: expected SecureString, got {p['Type']}")
                    self.check_or_drift(self.category, "SSM Parameter (SecureString)", param, drift)
                except ClientError as e:
                    code = e.response["Error"]["Code"]
                    if code == AwsErrorCode.PARAMETER_NOT_FOUND:
                        self.missing(self.category, "SSM Parameter (SecureString)", param)
                    else:
                        self.missing(self.category, "SSM Parameter (SecureString)", param, str(e))
