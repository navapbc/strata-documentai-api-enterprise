"""Read-only access to the document metadata DynamoDB table."""

from typing import Any

from boto3.dynamodb.conditions import Key

from documentai_api.config.env import get_aws_config
from documentai_api.schemas.document_metadata import DocumentMetadata
from documentai_api.utils.base_readonly_table import ReadOnlyTable


class DocumentMetadataTable(ReadOnlyTable):
    """Read-only access to the document metadata DynamoDB table."""

    table_name_env = "documentai_document_metadata_table_name"
    pk_field = "fileName"

    def _get_index(self, attr: str) -> str:
        name: str | None = getattr(get_aws_config(), attr, None)
        if not name:
            raise ValueError(f"{attr} not configured")
        return name

    def query_by_tenant(
        self,
        tenant_id: str,
        *,
        filter_expression: Any | None = None,
        limit: int = 50,
        scan_forward: bool = False,
        start_key: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        return self.query(
            key_condition=Key(DocumentMetadata.TENANT_ID).eq(tenant_id),
            filter_expression=filter_expression,
            index_name=self._get_index("documentai_document_metadata_tenant_index_name"),
            limit=limit,
            scan_forward=scan_forward,
            start_key=start_key,
        )

    def query_by_job_id(self, job_id: str) -> dict[str, Any] | None:
        items, _ = self.query(
            key_condition=Key(DocumentMetadata.JOB_ID).eq(job_id),
            index_name=self._get_index("documentai_document_metadata_job_id_index_name"),
            limit=1,
        )
        return items[0] if items else None
