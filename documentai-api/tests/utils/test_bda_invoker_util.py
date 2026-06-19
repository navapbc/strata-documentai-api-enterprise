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
                "BDA_PROJECT_ARN_ALL": "arn:aws:project",
                "BDA_PROFILE_ARN": "arn:aws:profile",
                "DOCUMENTAI_OUTPUT_LOCATION": "s3://output-bucket/path",
            },
        ),
        patch.object(bda_invoker_util, "_project_arns_cache", None),
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

        invocation_arn, project_arn = result
        assert invocation_arn == bda_invocation_arn
        assert project_arn == "arn:aws:project"
        mock_bda.invoke_data_automation_async.assert_called_once()


def test_invoke_bedrock_data_automation_document_truncation():
    bda_invocation_arn = "arn:aws:invocation:123"

    with (
        patch.dict(
            "os.environ",
            {
                "BDA_PROJECT_ARN": "arn:aws:project",
                "BDA_PROJECT_ARN_ALL": "arn:aws:project",
                "BDA_PROFILE_ARN": "arn:aws:profile",
                "DOCUMENTAI_OUTPUT_LOCATION": "s3://output-bucket/path",
            },
        ),
        patch.object(bda_invoker_util, "_project_arns_cache", None),
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

        invocation_arn, project_arn = result
        assert invocation_arn == bda_invocation_arn
        assert project_arn == "arn:aws:project"
        mock_truncate.assert_called_once_with(
            b"file_content", max_pages=int(ConfigDefaults.MAX_PAGES_PER_DOCUMENT)
        )
        mock_put_object.assert_called_once_with(
            bucket="test-bucket", key="test_truncated.pdf", body=b"truncated_content"
        )


def test_demo_upload_output_key_starts_with_expected_prefix():
    """Lock the cross-system contract: BDA output for demo uploads lands under
    processed/input/demo/ — matching the infra lifecycle rule prefix.

    BDA output is written to {DOCUMENTAI_OUTPUT_LOCATION}/{source_object_name}.
    For demo uploads, source_object_name is the full S3 key:
        input/demo/{tenant}/{file}
    So the output key becomes:
        processed/input/demo/{tenant}/{file}/...

    If this test fails, the infra S3 lifecycle rule (expire-demo-results) will
    stop matching and demo output won't auto-expire.
    """
    from unittest.mock import MagicMock, patch

    bda_invocation_arn = "arn:aws:invocation:demo-test"
    # Simulate a demo upload input key
    demo_source_object = "input/demo/test-tenant/doc-uuid.pdf"
    output_location = "s3://output-bucket/processed"

    with (
        patch.dict(
            "os.environ",
            {
                "BDA_PROJECT_ARN": "arn:aws:project",
                "BDA_PROJECT_ARN_ALL": "arn:aws:project",
                "BDA_PROFILE_ARN": "arn:aws:profile",
                "DOCUMENTAI_OUTPUT_LOCATION": output_location,
            },
        ),
        patch.object(bda_invoker_util, "_project_arns_cache", None),
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
        mock_get_page_count.return_value = 1

        bda_invoker_util.invoke_bedrock_data_automation("input-bucket", demo_source_object)

        # Assert the output s3Uri passed to BDA starts with the expected prefix
        call_kwargs = mock_bda.invoke_data_automation_async.call_args.kwargs
        output_s3_uri = call_kwargs["outputConfiguration"]["s3Uri"]

        # Must match: s3://output-bucket/processed/input/demo/...
        assert output_s3_uri == f"{output_location}/{demo_source_object}"
        # Extract just the key portion and verify the prefix that lifecycle rules target
        output_key = output_s3_uri.replace("s3://output-bucket/", "")
        assert output_key.startswith("processed/input/demo/"), (
            f"Demo output key '{output_key}' does not start with 'processed/input/demo/'. "
            "This means the infra lifecycle rule (expire-demo-results) won't match."
        )
