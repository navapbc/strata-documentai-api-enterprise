"""Schema for the tenants DynamoDB table."""

from documentai_api.utils.base_crud_table import BaseCrudTable


class TenantRecord:
    """Field names for the tenants DynamoDB table."""

    TENANT_ID = "tenantId"
    DISPLAY_NAME = "displayName"
    PRIMARY_CONTACT = "primaryContact"
    IS_ACTIVE = "isActive"
    EXTRACTION_CONFIDENCE_FLOOR = "extractionConfidenceFloor"
    MAX_WRITES_PER_DAY = "maxWritesPerDay"
    MAX_WRITES_PER_MONTH = "maxWritesPerMonth"
    CREATED_AT = "createdAt"
    UPDATED_AT = "updatedAt"
    OVERRIDE_BDA_PROJECT_ARN = "overrideBdaProjectArn"


class TenantsTable(BaseCrudTable):
    table_name_env = "tenants_table_name"
    pk_field = TenantRecord.TENANT_ID
    active_field = TenantRecord.IS_ACTIVE
    created_field = TenantRecord.CREATED_AT
    updated_field = TenantRecord.UPDATED_AT
    clearable_fields: frozenset[str] = frozenset(
        {
            TenantRecord.PRIMARY_CONTACT,
            TenantRecord.EXTRACTION_CONFIDENCE_FLOOR,
            TenantRecord.MAX_WRITES_PER_DAY,
            TenantRecord.MAX_WRITES_PER_MONTH,
            TenantRecord.OVERRIDE_BDA_PROJECT_ARN,
        }
    )
    super_admin_protected_fields: frozenset[str] = frozenset(
        {
            TenantRecord.IS_ACTIVE,
            TenantRecord.EXTRACTION_CONFIDENCE_FLOOR,
            TenantRecord.MAX_WRITES_PER_DAY,
            TenantRecord.MAX_WRITES_PER_MONTH,
        }
    )
