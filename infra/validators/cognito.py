"""Cognito validation."""

from botocore.exceptions import ClientError

from . import BaseValidator
from .constants import AwsErrorCode
from .discovery import filter_arns_by_service


class CognitoValidator(BaseValidator):
    category = "Cognito"

    def check_cognito(self):
        arns = self.component_resources.get("identity-provider", [])
        pool_arns = filter_arns_by_service(arns, "cognito-idp")

        if not pool_arns:
            self.warn(
                self.category,
                "Cognito User Pool",
                "component=identity-provider",
                "not discovered via tags",
            )
            return

        # Extract pool ID from ARN
        pool_id = pool_arns[0].split("/")[-1]

        try:
            detail = self.cognito.describe_user_pool(UserPoolId=pool_id)["UserPool"]
            pool_name = detail.get("Name", pool_id)

            drift = []
            if detail.get("MfaConfiguration") not in ("OPTIONAL", "ON"):
                drift.append(
                    f"mfa_configuration: expected OPTIONAL or ON, "
                    f"got {detail.get('MfaConfiguration')}"
                )
            adv = detail.get("UserPoolAddOns", {}).get("AdvancedSecurityMode", "OFF")
            if adv not in ("AUDIT", "ENFORCED"):
                drift.append(f"advanced_security_mode: expected AUDIT or ENFORCED, got {adv}")
            self.check_or_drift(self.category, "Cognito User Pool", pool_name, drift)

            # Check client exists
            clients = self.cognito.list_user_pool_clients(UserPoolId=pool_id, MaxResults=60)[
                "UserPoolClients"
            ]
            if clients:
                self.ok(self.category, "Cognito User Pool Client", clients[0]["ClientName"])
            else:
                self.missing(self.category, "Cognito User Pool Client", f"{pool_name}-client")

            # Cognito groups
            for group_name in ["super-admin", "tenant-admin"]:
                try:
                    self.cognito.get_group(GroupName=group_name, UserPoolId=pool_id)
                    self.ok(self.category, "Cognito Group", f"{pool_name}/{group_name}")
                except ClientError as e:
                    if e.response["Error"]["Code"] == AwsErrorCode.RESOURCE_NOT_FOUND:
                        self.missing(self.category, "Cognito Group", f"{pool_name}/{group_name}")
                    else:
                        self.missing(
                            self.category, "Cognito Group", f"{pool_name}/{group_name}", str(e)
                        )

        except ClientError as e:
            self.missing(self.category, "Cognito User Pool", pool_id, str(e))
