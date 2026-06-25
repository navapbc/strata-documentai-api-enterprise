"""SSM Parameter Store validation."""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.constants import AwsErrorCode
from validators.discovery import filter_arns_by_service


class SsmValidator(BaseValidator):
    category = "SSM"
    def check_ssm(self):

        # Config parameters (String type)
        config_spec = self.planned_tf_resources.get("config")
        if config_spec:
            ssm_params = config_spec.get_all_by_type("aws_ssm_parameter")
            config_param_names = [r.values.get("name") for r in ssm_params if r.values.get("name")]
        else:
            config_arns = self.component_resources.get("config", [])
            config_param_names = [
                arn.split(":parameter")[-1]
                for arn in filter_arns_by_service(config_arns, "ssm")
            ]

        if not config_param_names:
            self.missing(self.category, "SSM Parameter", "component=config (not discovered)")
        else:
            for param in config_param_names:
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
        secrets_spec = self.planned_tf_resources.get("secrets")
        if secrets_spec:
            ssm_params = secrets_spec.get_all_by_type("aws_ssm_parameter")
            secret_param_names = [r.values.get("name") for r in ssm_params if r.values.get("name")]
        else:
            secret_arns = self.component_resources.get("secrets", [])
            secret_param_names = [
                arn.split(":parameter")[-1]
                for arn in filter_arns_by_service(secret_arns, "ssm")
            ]

        if not secret_param_names:
            self.missing(self.category, "SSM Parameter (SecureString)", "component=secrets (not discovered)")
        else:
            for param in secret_param_names:
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
