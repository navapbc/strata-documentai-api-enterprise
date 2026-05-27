"""Schema for the extraction-rules DynamoDB table."""

from documentai_api.utils.base_crud_table import BaseCrudTable


class ExtractionRuleRecord:
    """Field names for the extraction-rules DynamoDB table."""

    TENANT_ID = "tenantId"
    DOCUMENT_TYPE = "documentType"
    REQUIRED_FIELDS = "requiredFields"
    OPTIONAL_FIELDS = "optionalFields"
    BLUEPRINT_ARN = "blueprintArn"
    CREATED_AT = "createdAt"
    UPDATED_AT = "updatedAt"


class ExtractionRulesTable(BaseCrudTable):
    table_name_env = "extraction_rules_table_name"
    pk_field = ExtractionRuleRecord.TENANT_ID
    sk_field = ExtractionRuleRecord.DOCUMENT_TYPE
    active_field = ""  # No active field - rules are hard-deleted
