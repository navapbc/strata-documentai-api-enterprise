"""Schema for the document-categories DynamoDB table."""

from documentai_api.utils.base_crud_table import BaseCrudTable


class DocumentCategoryRecord:
    """Field names for the document-categories DynamoDB table."""

    TENANT_ID = "tenantId"
    CATEGORY_NAME = "categoryName"
    DISPLAY_NAME = "displayName"
    DESCRIPTION = "description"
    IS_ACTIVE = "isActive"
    IS_AUTO_REGISTERED = "isAutoRegistered"
    PROCESSING_PERCENTAGE = "processingPercentage"
    CREATED_AT = "createdAt"
    UPDATED_AT = "updatedAt"


class DocumentCategoriesTable(BaseCrudTable):
    table_name_env = "document_categories_table_name"
    pk_field = DocumentCategoryRecord.TENANT_ID
    sk_field = DocumentCategoryRecord.CATEGORY_NAME
    active_field = DocumentCategoryRecord.IS_ACTIVE
    created_field = DocumentCategoryRecord.CREATED_AT
    updated_field = DocumentCategoryRecord.UPDATED_AT
