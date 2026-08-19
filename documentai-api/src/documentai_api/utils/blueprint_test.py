import json
from dataclasses import dataclass

from documentai_api.config.env import get_aws_config
from documentai_api.logging import get_logger
from documentai_api.services import s3 as s3_service

logger = get_logger(__name__)


@dataclass
class TestMetadata:
    invocation_arn: str
    tenant_id: str
    document_type: str | None
    test_key: str


def metadata_key(test_id: str) -> str:
    return f"test-runner/{test_id}/metadata.json"


def store_test_metadata(
    test_id: str,
    invocation_arn: str,
    tenant_id: str | None,
    document_type: str | None,
    test_key: str,
) -> None:
    s3_service.put_object(
        get_aws_config().get_input_bucket_name(),
        metadata_key(test_id),
        json.dumps(
            {
                "invocationArn": invocation_arn,
                "tenantId": tenant_id or "",
                "documentType": document_type or "",
                "testKey": test_key,
            }
        ).encode(),
        content_type="application/json",
    )


def get_test_metadata(test_id: str) -> TestMetadata | None:
    try:
        response = s3_service.get_object(
            get_aws_config().get_input_bucket_name(), metadata_key(test_id)
        )
        data = json.loads(response["Body"].read())
        return TestMetadata(
            invocation_arn=data["invocationArn"],
            tenant_id=data["tenantId"],
            document_type=data.get("documentType") or None,
            test_key=data["testKey"],
        )
    except Exception:
        return None


def cleanup_test(test_id: str, test_key: str) -> None:
    """Clean up test file from S3 — metadata cleaned up by S3 lifecycle rule."""
    bucket = get_aws_config().get_input_bucket_name()
    try:
        s3_service.delete_object(bucket, test_key)
    except Exception:
        logger.warning(f"Failed to cleanup test file: s3://{bucket}/{test_key}")
