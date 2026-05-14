from unittest.mock import MagicMock, patch

from documentai_api.config.constants import ConfigDefaults
from documentai_api.utils import bda_invoker as bda_invoker_util


def test_invoke_bedrock_data_automation_single_page():
    bda_invocation_arn = "arn:aws:invocation:123"

    with (
        patch.dict(
            "os.environ",
            {
                "BDA_PROJECT_ARN": "arn:aws:project",
                "BDA_PROFILE_ARN": "arn:aws:profile",
                "DOCUMENTAI_OUTPUT_LOCATION": "s3://output-bucket/path",
            },
        ),
        patch(
            "documentai_api.utils.bda_invoker.AWSClientFactory.get_bda_runtime_client"
        ) as mock_get_bda_client,
        patch("documentai_api.services.s3.get_file_bytes") as mock_get_file_bytes,
        patch(
            "documentai_api.utils.bda_invoker.document_utils.get_page_count"
        ) as mock_get_page_count,
    ):
        mock_bda = MagicMock()
        mock_bda.invoke_data_automation_async.return_value = {"invocationArn": bda_invocation_arn}
        mock_get_bda_client.return_value = mock_bda

        mock_get_file_bytes.return_value = b"file_content"
        mock_get_page_count.return_value = 3

        result = bda_invoker_util.invoke_bedrock_data_automation("test-bucket", "test.pdf")

        assert result == bda_invocation_arn
        mock_bda.invoke_data_automation_async.assert_called_once()


def test_invoke_bedrock_data_automation_document_truncation():
    bda_invocation_arn = "arn:aws:invocation:123"

    with (
        patch.dict(
            "os.environ",
            {
                "BDA_PROJECT_ARN": "arn:aws:project",
                "BDA_PROFILE_ARN": "arn:aws:profile",
                "DOCUMENTAI_OUTPUT_LOCATION": "s3://output-bucket/path",
            },
        ),
        patch(
            "documentai_api.utils.bda_invoker.AWSClientFactory.get_bda_runtime_client"
        ) as mock_get_bda_client,
        patch("documentai_api.services.s3.get_file_bytes") as mock_get_file_bytes,
        patch("documentai_api.services.s3.put_object") as mock_put_object,
        patch(
            "documentai_api.utils.bda_invoker.document_utils.get_page_count"
        ) as mock_get_page_count,
        patch("documentai_api.utils.bda_invoker.document_utils.truncate_to_pages") as mock_truncate,
    ):
        mock_bda = MagicMock()
        mock_bda.invoke_data_automation_async.return_value = {"invocationArn": bda_invocation_arn}
        mock_get_bda_client.return_value = mock_bda

        mock_get_file_bytes.return_value = b"file_content"
        mock_get_page_count.return_value = 10
        mock_truncate.return_value = b"truncated_content"

        result = bda_invoker_util.invoke_bedrock_data_automation("test-bucket", "test.pdf")

        assert result == bda_invocation_arn
        mock_truncate.assert_called_once_with(
            b"file_content", max_pages=int(ConfigDefaults.MAX_PAGES_PER_DOCUMENT)
        )
        mock_put_object.assert_called_once_with(
            bucket="test-bucket", key="test_truncated.pdf", body=b"truncated_content"
        )
