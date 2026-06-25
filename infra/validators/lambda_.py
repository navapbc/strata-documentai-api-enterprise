"""Lambda function validation."""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.constants import AwsErrorCode
from validators.discovery import extract_name_from_arn, filter_arns_by_service


class LambdaValidator(BaseValidator):
    category = "Lambda"
    def _check_lambda(self, name: str, memory: int, timeout: int):
        try:
            cfg = self.lambda_client.get_function(FunctionName=name)["Configuration"]
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == AwsErrorCode.RESOURCE_NOT_FOUND:
                self.missing(self.category, "Lambda Function", name)
            else:
                self.missing(self.category, "Lambda Function", name, str(e))
            return

        drift = []
        if cfg.get("PackageType") != "Image":
            drift.append(f"package_type: expected Image, got {cfg.get('PackageType')}")
        if cfg.get("MemorySize") != memory:
            drift.append(f"memory_size: expected {memory}, got {cfg.get('MemorySize')}")
        if cfg.get("Timeout") != timeout:
            drift.append(f"timeout: expected {timeout}, got {cfg.get('Timeout')}")

        self.check_or_drift(self.category, "Lambda Function", name, drift)

    def _get_lambda_name(self, component_tag: str) -> str | None:
        """Get the Lambda function name for a component, filtering out non-Lambda ARNs."""
        arns = self.component_resources.get(component_tag, [])
        lambda_arns = filter_arns_by_service(arns, "lambda")
        if not lambda_arns:
            return None
        return extract_name_from_arn(lambda_arns[0])

    def check_lambdas(self):

        # Derive Lambda specs from expected.json
        for component_name, spec in sorted(self.planned_tf_resources.items()):
            lmb = spec.get_by_type("aws_lambda_function")
            if not lmb:
                continue

            v = lmb.values
            name = self._get_lambda_name(component_name)
            if not name:
                # Fall back to name from spec
                name = v.get("function_name")
                if not name:
                    self.missing(self.category, "Lambda Function", f"component={component_name} (not discovered)")
                    continue

            self._check_lambda(
                name,
                memory=v.get("memory_size", 512),
                timeout=v.get("timeout", 300),
            )
