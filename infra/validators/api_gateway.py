"""API Gateway validation."""

from botocore.exceptions import ClientError

from . import BaseValidator
from .discovery import extract_name_from_arn, filter_arns_by_service


class ApiGatewayValidator(BaseValidator):
    category = "API Gateway"

    def check_api_gateway(self):
        arns = self.component_resources.get("api-gateway", [])
        apigw_arns = filter_arns_by_service(arns, "apigateway")

        if not apigw_arns:
            self.warn(self.category, "HTTP API", "component=api-gateway", "not discovered via tags")
            return

        api_id = extract_name_from_arn(apigw_arns[0])
        try:
            match = self.apigw.get_api(ApiId=api_id)
            drift = []
            if match.get("ProtocolType") != "HTTP":
                drift.append(f"protocol_type: expected HTTP, got {match.get('ProtocolType')}")
            self.check_or_drift(self.category, "HTTP API", match.get("Name", api_id), drift)
        except ClientError as e:
            self.missing(self.category, "HTTP API", api_id, str(e))
