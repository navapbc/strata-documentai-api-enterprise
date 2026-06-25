"""DynamoDB table validation."""

from botocore.exceptions import ClientError

from validators import BaseValidator
from validators.constants import AwsErrorCode


class DynamoDBValidator(BaseValidator):
    def _check_ddb(
        self,
        name: str,
        hash_key: str,
        sort_key: str | None = None,
        gsi_names: list[str] | None = None,
        ttl_attr: str | None = None,
    ):
        cat = "DynamoDB"
        try:
            table = self.ddb.describe_table(TableName=name)["Table"]
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == AwsErrorCode.RESOURCE_NOT_FOUND:
                self.missing(cat, "DynamoDB Table", name)
            else:
                self.missing(cat, "DynamoDB Table", name, str(e))
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

        self.check_or_drift(cat, "DynamoDB Table", name, drift)

    def check_dynamodb(self):
        tables = {
            "document-metadata": {
                "hash_key": "fileName",
                "gsi_names": [
                    "JobIdIndex",
                    "ExternalDocumentIdIndex",
                    "BdaInvocationIdIndex",
                    "TenantIdIndex",
                ],
                "ttl_attr": "ttl",
            },
            "api-keys": {"hash_key": "keyHash"},
            "tenants": {"hash_key": "tenantId"},
            "audit-events": {
                "hash_key": "tenantId",
                "sort_key": "timestamp#eventId",
                "gsi_names": ["action-timestamp-index"],
                "ttl_attr": "ttl",
            },
            "extraction-rules": {"hash_key": "tenantId", "sort_key": "documentType"},
            "document-categories": {"hash_key": "tenantId", "sort_key": "categoryName"},
            "document-batches": {
                "hash_key": "batchId",
                "gsi_names": ["StatusCreatedAtIndex", "TenantIndex"],
                "ttl_attr": "ttl",
            },
            "document-builds": {
                "hash_key": "buildId",
                "sort_key": "pageNumber",
                "gsi_names": ["TenantIndex", "ExternalReferenceIdIndex"],
                "ttl_attr": "ttl",
            },
        }

        for component_tag, config in tables.items():
            name = self.get_resource_name_by_component_tag(component_tag)
            if not name:
                self.missing(
                    "DynamoDB", "DynamoDB Table", f"component={component_tag} (not discovered)"
                )
            else:
                self._check_ddb(name, **config)
