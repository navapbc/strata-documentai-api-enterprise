"""API Gateway validation."""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.discovery import filter_arns_by_service


class ApiGatewayValidator(BaseValidator):
    def check_api_gateway(self):
        cat = "API Gateway"
        # The api-gateway component has both lambda and apigatewayv2 resources
        arns = self.component_resources.get("api-gateway", [])
        apigw_arns = filter_arns_by_service(arns, "apigateway")

        if not apigw_arns:
            # Fall back to searching by name via API
            name = self.get_resource_name_by_component_tag("api-gateway")
            if not name:
                self.missing(cat, "HTTP API", "component=api-gateway (not discovered)")
                return
        else:
            # Extract API ID from ARN: arn:aws:apigateway:region::/apis/api-id
            api_id = apigw_arns[0].split("/")[-1]
            try:
                match = self.apigw.get_api(ApiId=api_id)
                drift = []
                if match.get("ProtocolType") != "HTTP":
                    drift.append(
                        f"protocol_type: expected HTTP, got {match.get('ProtocolType')}"
                    )
                self.check_or_drift(cat, "HTTP API", match.get("Name", api_id), drift)
                return
            except ClientError as e:
                self.missing(cat, "HTTP API", api_id, str(e))
                return

        # Fallback: paginated search
        try:
            apis = []
            next_token = None
            while True:
                kwargs = {}
                if next_token:
                    kwargs["NextToken"] = next_token
                resp = self.apigw.get_apis(**kwargs)
                apis.extend(resp.get("Items", []))
                next_token = resp.get("NextToken")
                if not next_token:
                    break
            match = next((a for a in apis if a["Name"] == name), None)
            if not match:
                self.missing(cat, "HTTP API", name)
                return
            drift = []
            if match.get("ProtocolType") != "HTTP":
                drift.append(f"protocol_type: expected HTTP, got {match.get('ProtocolType')}")
            self.check_or_drift(cat, "HTTP API", name, drift)
        except ClientError as e:
            self.missing(cat, "HTTP API", name, str(e))
