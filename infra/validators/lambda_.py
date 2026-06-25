"""Lambda function validation."""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.constants import AwsErrorCode
from validators.discovery import extract_name_from_arn, filter_arns_by_service


class LambdaValidator(BaseValidator):
    def _check_lambda(self, name: str, memory: int, timeout: int):
        cat = "Lambda"
        try:
            cfg = self.lmb.get_function(FunctionName=name)["Configuration"]
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == AwsErrorCode.RESOURCE_NOT_FOUND:
                self.missing(cat, "Lambda Function", name)
            else:
                self.missing(cat, "Lambda Function", name, str(e))
            return

        drift = []
        if cfg.get("PackageType") != "Image":
            drift.append(f"package_type: expected Image, got {cfg.get('PackageType')}")
        if cfg.get("MemorySize") != memory:
            drift.append(f"memory_size: expected {memory}, got {cfg.get('MemorySize')}")
        if cfg.get("Timeout") != timeout:
            drift.append(f"timeout: expected {timeout}, got {cfg.get('Timeout')}")

        self.check_or_drift(cat, "Lambda Function", name, drift)

    def _get_lambda_name(self, component_tag: str) -> str | None:
        """Get the Lambda function name for a component, filtering out non-Lambda ARNs."""
        arns = self.component_resources.get(component_tag, [])
        lambda_arns = filter_arns_by_service(arns, "lambda")
        if not lambda_arns:
            return None
        return extract_name_from_arn(lambda_arns[0])

    def check_lambdas(self):
        lambdas = {
            "api-gateway": {"memory": 1024, "timeout": 30},
            "document-processor": {"memory": 512, "timeout": 300},
            "bda-result-processor": {"memory": 512, "timeout": 300},
            "metrics-processor": {"memory": 512, "timeout": 300},
            "metrics-aggregator": {"memory": 512, "timeout": 300},
        }
        for component_tag, config in lambdas.items():
            name = self._get_lambda_name(component_tag)
            if not name:
                self.missing(
                    "Lambda", "Lambda Function", f"component={component_tag} (not discovered)"
                )
            else:
                self._check_lambda(name, **config)
