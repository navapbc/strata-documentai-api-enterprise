"""Schema for blueprint DynamoDB tables."""

from documentai_api.config.env import get_aws_config
from documentai_api.utils.base_crud_table import BaseCrudTable


class BlueprintRecord:
    """Field names for the blueprints table."""

    TENANT_ID = "tenantId"
    BLUEPRINT_ID = "blueprintId"
    DESCRIPTION = "description"
    DOCUMENT_TYPE = "documentType"
    FIELDS = "blueprintFields"
    STATUS = "blueprintStatus"  # BlueprintStatus enum
    IS_ACTIVE = "isActive"
    BLUEPRINT_ARN = "blueprintArn"
    PROJECT_ARN = "projectArn"
    CREATED_AT = "createdAt"
    UPDATED_AT = "updatedAt"


class AuthoredBlueprintsTable(BaseCrudTable):
    table_name_env = "blueprints_table_name"
    pk_field = BlueprintRecord.TENANT_ID
    sk_field = BlueprintRecord.BLUEPRINT_ID
    active_field = BlueprintRecord.IS_ACTIVE

    def document_type_index(self) -> str:
        name: str | None = get_aws_config().blueprints_document_type_index_name
        if not name:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Storage not configured"
            )
        return name
