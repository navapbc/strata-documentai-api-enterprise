"""DynamoDB table validation."""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.constants import AwsErrorCode
from validators.discovery import extract_name_from_arn, filter_arns_by_service


class DynamoDBValidator(BaseValidator):
    category = "DynamoDB"

    def _check_ddb(
        self,
        name: str,
        hash_key: str,
        sort_key: str | None = None,
        gsi_names: list[str] | None = None,
        ttl_attr: str | None = None,
    ):
        try:
            table = self.ddb.describe_table(TableName=name)["Table"]
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == AwsErrorCode.RESOURCE_NOT_FOUND:
                self.missing(self.category, "DynamoDB Table", name)
            else:
                self.missing(self.category, "DynamoDB Table", name, str(e))
            return

        drift = []

        billing = table.get("BillingModeSummary", {}).get("BillingMode", "PROVISIONED")
        if billing != "PAY_PER_REQUEST":
            drift.append(f"billing_mode: expected PAY_PER_REQUEST, got {billing}")

        keys = {k["AttributeName"]: k["KeyType"] for k in table.get("KeySchema", [])}
        if keys.get(hash_key) != "HASH":
            drift.append(f"hash_key: expected '{hash_key}', actual keys={keys}")
        if sort_key and keys.get(sort_key) != "RANGE":
            drift.append(f"sort_key: expected '{sort_key}', not found in {list(keys)}")

        sse = table.get("SSEDescription", {}).get("Status", "DISABLED")
        if sse not in ("ENABLED", "UPDATING"):
            drift.append("server_side_encryption: KMS not enabled")

        try:
            pitr = self.ddb.describe_continuous_backups(TableName=name)
            pitr_status = pitr["ContinuousBackupsDescription"][
                "PointInTimeRecoveryDescription"
            ]["PointInTimeRecoveryStatus"]
            if pitr_status != "ENABLED":
                drift.append("point_in_time_recovery: not enabled")
        except ClientError:
            drift.append("Cannot read PITR status")

        if not table.get("DeletionProtectionEnabled", False):
            drift.append("deletion_protection_enabled: should be true")

        if gsi_names:
            actual_gsis = {g["IndexName"] for g in table.get("GlobalSecondaryIndexes", [])}
            drift.extend(
                f"GSI missing: '{gsi}'" for gsi in gsi_names if gsi not in actual_gsis
            )

        if ttl_attr:
            try:
                ttl = self.ddb.describe_time_to_live(TableName=name)["TimeToLiveDescription"]
                if ttl.get("TimeToLiveStatus") not in ("ENABLED", "ENABLING"):
                    drift.append(f"ttl: not enabled (expected attribute '{ttl_attr}')")
                elif ttl.get("AttributeName") != ttl_attr:
                    drift.append(
                        f"ttl attribute: expected '{ttl_attr}', got '{ttl.get('AttributeName')}'"
                    )
            except ClientError:
                drift.append("Cannot read TTL configuration")

        self.check_or_drift(self.category, "DynamoDB Table", name, drift)

    def check_dynamodb(self):
        for component_name, spec in sorted(self.planned_tf_resources.items()):
            ddb = spec.get_by_type("aws_dynamodb_table")
            if not ddb:
                continue

            v = ddb.values
            arns = self.component_resources.get(component_name, [])
            ddb_arns = filter_arns_by_service(arns, "dynamodb")
            if ddb_arns:
                name = extract_name_from_arn(ddb_arns[0])
            else:
                name = v.get("name")

            if not name:
                self.missing(self.category, "DynamoDB Table", f"component={component_name} (not discovered)")
                continue

            gsi_names = [g["name"] for g in v.get("global_secondary_index", [])]
            ttl_list = v.get("ttl", [])
            ttl_attr = ttl_list[0].get("attribute_name") if ttl_list else None

            self._check_ddb(
                name,
                hash_key=v["hash_key"],
                sort_key=v.get("range_key"),
                gsi_names=gsi_names or None,
                ttl_attr=ttl_attr,
            )
