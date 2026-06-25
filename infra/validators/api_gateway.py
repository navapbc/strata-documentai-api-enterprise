"""API Gateway validation."""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.discovery import extract_name_from_arn, filter_arns_by_service


class ApiGatewayValidator(BaseValidator):
    category = "API Gateway"

    def check_api_gateway(self):
        arns = self.component_resources.get("api-gateway", [])
        apigw_arns = filter_arns_by_service(arns, "apigateway")

        if apigw_arns:
            api_id = extract_name_from_arn(apigw_arns[0])
            try:
                match = self.apigw.get_api(ApiId=api_id)
                drift = []
                if match.get("ProtocolType") != "HTTP":
                    drift.append(
                        f"protocol_type: expected HTTP, got {match.get('ProtocolType')}"
                    )
                self.check_or_drift(self.category, "HTTP API", match.get("Name", api_id), drift)
                return
            except ClientError as e:
                self.missing(self.category, "HTTP API", api_id, str(e))
                return

        # Fall back to expected.json
        spec = self.planned_tf_resources.get("api-gateway")
        if spec:
            apigw_res = spec.get_by_type("aws_apigatewayv2_api")
            if apigw_res:
                name = apigw_res.values.get("name")
                if name:
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
                            self.missing(self.category, "HTTP API", name)
                            return
                        drift = []
                        if match.get("ProtocolType") != "HTTP":
                            drift.append(
                                f"protocol_type: expected HTTP, got {match.get('ProtocolType')}"
                            )
                        self.check_or_drift(self.category, "HTTP API", name, drift)
                        return
                    except ClientError as e:
                        self.missing(self.category, "HTTP API", name, str(e))
                        return

        self.missing(self.category, "HTTP API", "component=api-gateway (not discovered)")
