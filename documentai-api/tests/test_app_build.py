"""Tests for document build endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from documentai_api.app import app
from documentai_api.utils.models import PageMetadata
from documentai_api.utils.uploads import ImageConversionError

client = TestClient(app)


@pytest.fixture(autouse=True)
def _disable_auth(disable_auth):
    pass


@pytest.fixture
def mock_document_build_upload():
    """Mock common document build page-upload dependencies."""
    with (
        patch("documentai_api.utils.uploads.filetype.guess_mime") as mock_guess,
        patch(
            "documentai_api.app_build.upload_document_for_processing",
            new_callable=AsyncMock,
        ) as mock_upload,
        patch(
            "documentai_api.app_build.upsert_document_build_page",
            new_callable=AsyncMock,
        ) as mock_upsert,
        patch("documentai_api.app_build.get_document_build_pages", return_value=[]),
    ):
        mock_guess.return_value = "application/pdf"

        yield {
            "magic": mock_guess,
            "upload": mock_upload,
            "upsert": mock_upsert,
        }


@pytest.fixture
def mock_document_build_submit():
    """Mock common document build submit dependencies."""
    import io

    with (
        patch("documentai_api.app_build.get_document_build_pages") as mock_get_pages,
        patch("documentai_api.app_build.merge_pages_to_pdf") as mock_merge,
        patch(
            "documentai_api.app_build.upload_document_for_processing",
            new_callable=AsyncMock,
        ) as mock_upload,
        patch("documentai_api.app_build.mark_document_build_submitted") as mock_mark_submitted,
        patch("documentai_api.config.env.AWSEnvConfig") as mock_aws_config,
    ):
        mock_merge.return_value = io.BytesIO(b"merged pdf bytes")
        mock_aws_config.return_value.documentai_input_location = "s3://test-bucket/input"

        yield {
            "get_pages": mock_get_pages,
            "merge": mock_merge,
            "upload": mock_upload,
            "mark_submitted": mock_mark_submitted,
            "aws_config": mock_aws_config,
        }


def create_page_metadata(
    page_number: int, build_id: str = "test-build-id", category: str | None = None
) -> PageMetadata:
    """Helper to create PageMetadata for tests."""
    return PageMetadata(
        page_number=page_number,
        s3_key=f"builds/{build_id}/page-{page_number}.pdf",
        s3_bucket_name="test-bucket",
        category=category,
    )


def test_create_build(document_build_ddb_table):
    with patch("documentai_api.app_build.create_document_build") as mock_create:
        mock_create.return_value = "fake-build-id"
        response = client.post("/v1/builds")

    assert response.status_code == 200
    result = response.json()
    assert "buildId" in result
    assert result["message"] == "Build created successfully"


def test_create_build_with_external_fields(document_build_ddb_table):
    """Test create build passes external fields to create_document_build."""
    with patch("documentai_api.app_build.create_document_build") as mock_create:
        mock_create.return_value = "fake-build-id"
        data = {
            "external_document_id": "ext-doc-build",
            "external_system_id": "ext-sys-build",
            "ai_consent_flag": "true",
        }
        response = client.post("/v1/builds", data=data)

    assert response.status_code == 200
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["external_document_id"] == "ext-doc-build"
    assert call_kwargs["external_system_id"] == "ext-sys-build"
    assert call_kwargs["ai_consent_flag"] is True


@pytest.mark.parametrize(
    ("build_id", "page_number", "expected_build"),
    [
        (None, 1, None),  # new build - buildId will be generated
        ("test-build-id", 2, "test-build-id"),  # existing build
    ],
)
def test_upload_document_build_page_builds(
    document_build_ddb_table, mock_document_build_upload, build_id, page_number, expected_build
):
    """Test uploading pages to new and existing builds."""
    files = {"file": ("page.pdf", b"fake pdf", "application/pdf")}
    data = {"page_number": page_number}
    response = client.post("/v1/builds/test-build-id/pages", files=files, data=data)

    assert response.status_code == 200
    result = response.json()
    assert "buildId" in result
    if expected_build:
        assert result["buildId"] == expected_build
    assert result["pageNumber"] == page_number
    assert "uploaded successfully" in result["message"].lower()


@pytest.mark.parametrize(
    ("file_type", "file_name"),
    [
        ("application/zip", "test.zip"),
        ("text/plain", "test.txt"),
    ],
)
def test_upload_document_build_page_invalid_file_type(
    document_build_ddb_table, mock_document_build_upload, file_type, file_name
):
    """Test document build upload with invalid file types."""
    mock_document_build_upload["magic"].return_value = file_type

    files = {"file": (file_name, b"fake content", file_type)}
    data = {"page_number": 1}
    response = client.post("/v1/builds/test-build-id/pages", files=files, data=data)

    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


@pytest.mark.parametrize(
    ("overwrite", "upsert_raises", "expected_status"),
    [
        (False, True, 409),  # duplicate without overwrite -> conflict from conditional write
        (True, False, 200),  # duplicate with overwrite -> success
        (False, False, 200),  # new page -> success
    ],
)
def test_upload_document_build_page_overwrite_scenarios(
    document_build_ddb_table, mock_document_build_upload, overwrite, upsert_raises, expected_status
):
    """Test document build upload duplicate/overwrite scenarios."""
    if upsert_raises:
        mock_document_build_upload["upsert"].side_effect = HTTPException(
            status_code=409,
            detail="Page 1 already exists for build test-build-id. Set overwrite=true to replace.",
        )

    files = {"file": ("page1.pdf", b"fake pdf", "application/pdf")}
    data = {"page_number": 1, "overwrite": overwrite}
    response = client.post("/v1/builds/test-build-id/pages", files=files, data=data)

    assert response.status_code == expected_status
    if expected_status == 409:
        assert "already exists" in response.json()["detail"]


def test_upload_document_build_page_with_category(
    document_build_ddb_table, mock_document_build_upload
):
    """Test document build upload with document category."""
    files = {"file": ("page1.pdf", b"fake pdf", "application/pdf")}
    data = {"page_number": 1, "category": "income"}
    response = client.post("/v1/builds/test-build-id/pages", files=files, data=data)

    assert response.status_code == 200
    mock_document_build_upload["upsert"].assert_called_once()


def test_submit_document_build_not_found(document_build_ddb_table, mock_document_build_submit):
    """Test submitting build with no pages."""
    mock_document_build_submit["get_pages"].return_value = []

    response = client.post("/v1/builds/nonexistent-build/submit")

    assert response.status_code == 400
    assert "no pages" in response.json()["detail"].lower()


def test_submit_document_build_synchronous(document_build_ddb_table, mock_document_build_submit):
    """Test synchronous document build submission (wait=true)."""
    from documentai_api.models.api_responses import JobStatusResponse

    with patch(
        "documentai_api.utils.jobs.poll_for_completion",
        new_callable=AsyncMock,
    ) as mock_get_results:
        mock_document_build_submit["get_pages"].return_value = [
            create_page_metadata(1, category="income"),
        ]
        mock_get_results.return_value = JobStatusResponse(
            job_id="test-job-id",
            job_status="success",
            message="Processing complete",
        )

        response = client.post("/v1/builds/test-build-id/submit?wait=true")

    assert response.status_code == 200
    assert response.json()["jobStatus"] == "success"


def test_submit_document_build_with_category(document_build_ddb_table, mock_document_build_submit):
    """Test submit uses first non-None category from pages."""
    from documentai_api.config.constants import DocumentCategory

    mock_document_build_submit["get_pages"].return_value = [
        create_page_metadata(1, category="income"),
        create_page_metadata(2),
    ]

    response = client.post("/v1/builds/test-build-id/submit")

    assert response.status_code == 200
    mock_document_build_submit["upload"].assert_called_once()

    # verify category was converted to enum
    call_args = mock_document_build_submit["upload"].call_args
    assert call_args.kwargs["user_provided_document_category"] == DocumentCategory.INCOME


@pytest.mark.parametrize(
    ("mock_method", "error"),
    [
        ("merge", Exception("PDF merge failed")),
        ("upload", HTTPException(status_code=500, detail="Upload failed")),
    ],
)
def test_submit_document_build_errors(
    document_build_ddb_table, mock_document_build_submit, mock_method, error
):
    """Test error handling during document build submit."""
    mock_document_build_submit["get_pages"].return_value = [
        create_page_metadata(1, category="income"),
        create_page_metadata(2),
    ]
    mock_document_build_submit[mock_method].side_effect = error

    response = client.post("/v1/builds/test-build-id/submit")

    assert response.status_code == 500


def test_submit_document_build_already_submitted(
    document_build_ddb_table, mock_document_build_submit
):
    """Test submitting a build that was already submitted."""
    mock_document_build_submit["mark_submitted"].side_effect = HTTPException(
        status_code=400,
        detail="Build test-build-id has already been submitted for processing",
    )

    response = client.post("/v1/builds/test-build-id/submit")

    assert response.status_code == 400
    assert "already been submitted" in response.json()["detail"]

    # verify we didn't try to merge or upload
    mock_document_build_submit["merge"].assert_not_called()
    mock_document_build_submit["upload"].assert_not_called()


def test_submit_document_build_success(document_build_ddb_table, mock_document_build_submit):
    """Test successful document build submission."""
    mock_document_build_submit["get_pages"].return_value = [
        create_page_metadata(1, category="income"),
        create_page_metadata(2),
    ]

    response = client.post("/v1/builds/test-build-id/submit")

    assert response.status_code == 200
    result = response.json()
    assert "jobId" in result
    assert result["buildId"] == "test-build-id"
    assert result["jobStatus"] == "not_started"
    assert result["pageCount"] == 2

    # verify build was marked as submitted
    mock_document_build_submit["mark_submitted"].assert_called_with("test-build-id")


def test_upload_document_build_page_error_handling(
    document_build_ddb_table, mock_document_build_upload
):
    """Test error handling during document build page upload."""
    mock_document_build_upload["upload"].side_effect = Exception("S3 upload failed")

    files = {"file": ("page1.pdf", b"fake pdf", "application/pdf")}
    data = {"page_number": 1}
    response = client.post("/v1/builds/test-build-id/pages", files=files, data=data)

    assert response.status_code == 500
    assert "Failed to upload page" in response.json()["detail"]


def test_get_document_build_success(document_build_ddb_table):
    """Test getting build details."""
    pages = [
        create_page_metadata(1, category="income"),
        create_page_metadata(2),
    ]

    with (
        patch("documentai_api.app_build.get_document_build_pages", return_value=pages),
        patch("documentai_api.app_build.is_document_build_submitted", return_value=False),
    ):
        response = client.get("/v1/builds/test-build-id")

    assert response.status_code == 200
    result = response.json()
    assert result["buildId"] == "test-build-id"
    assert result["pageCount"] == 2
    assert len(result["pages"]) == 2
    assert result["pages"][0]["pageNumber"] == 1
    assert result["pages"][0]["category"] == "income"


@pytest.mark.parametrize(
    ("mock_side_effect", "expected_status"),
    [
        (True, 204),  # success - return value
        (False, 404),  # not found - return value
        (
            ValueError("Cannot delete - build already submitted"),
            400,
        ),  # already submitted - exception
    ],
)
def test_delete_document_build_page(document_build_ddb_table, mock_side_effect, expected_status):
    """Test deleting a page."""
    with patch("documentai_api.app_build.delete_document_build_page") as mock_delete:
        if isinstance(mock_side_effect, Exception):
            mock_delete.side_effect = mock_side_effect
        else:
            mock_delete.return_value = mock_side_effect

        response = client.delete("/v1/builds/test-build-id/pages/1")

        assert response.status_code == expected_status
        if expected_status == 400:
            assert "already" in response.json()["detail"]


@pytest.mark.parametrize(
    ("mock_side_effect", "expected_status"),
    [
        (True, 204),  # success
        (False, 404),  # not found
        (ValueError("Cannot delete - build already submitted"), 400),  # already submitted
    ],
)
def test_delete_document_build(document_build_ddb_table, mock_side_effect, expected_status):
    """Test deleting entire document build."""
    with patch("documentai_api.app_build.delete_document_build") as mock_delete:
        if isinstance(mock_side_effect, Exception):
            mock_delete.side_effect = mock_side_effect
        else:
            mock_delete.return_value = mock_side_effect

        response = client.delete("/v1/builds/test-build-id")

        assert response.status_code == expected_status
        if expected_status == 400:
            assert "already" in response.json()["detail"]


def test_get_document_build_includes_status_and_filename(document_build_ddb_table):
    """Test GET build returns buildStatus and originalFileName."""
    pages = [
        PageMetadata(
            page_number=1,
            s3_key="builds/test-build-id/page-1.pdf",
            s3_bucket_name="test-bucket",
            original_file_name="paystub.pdf",
            category="income",
        ),
        PageMetadata(
            page_number=2,
            s3_key="builds/test-build-id/page-2.pdf",
            s3_bucket_name="test-bucket",
            original_file_name="w2.pdf",
        ),
    ]

    with (
        patch("documentai_api.app_build.get_document_build_pages", return_value=pages),
        patch("documentai_api.app_build.is_document_build_submitted", return_value=False),
    ):
        response = client.get("/v1/builds/test-build-id")

    assert response.status_code == 200
    result = response.json()
    assert result["buildStatus"] == "not_submitted"
    assert result["pages"][0]["originalFileName"] == "paystub.pdf"
    assert result["pages"][1]["originalFileName"] == "w2.pdf"


@pytest.mark.parametrize(
    ("is_submitted", "expected_status"),
    [
        (True, "submitted"),
        (False, "not_submitted"),
    ],
)
def test_get_document_build_status(document_build_ddb_table, is_submitted, expected_status):
    """Test GET build returns correct buildStatus."""
    pages = [create_page_metadata(1, category="income")]

    with (
        patch("documentai_api.app_build.get_document_build_pages", return_value=pages),
        patch("documentai_api.app_build.is_document_build_submitted", return_value=is_submitted),
    ):
        response = client.get("/v1/builds/test-build-id")

    assert response.status_code == 200
    assert response.json()["buildStatus"] == expected_status


def test_upload_document_build_pages_batch_success(
    document_build_ddb_table, mock_document_build_upload
):
    """Test batch upload of multiple pages."""
    with patch("documentai_api.app_build.get_document_build_pages", return_value=[]):
        files = [
            ("files", ("page1.pdf", b"fake pdf 1", "application/pdf")),
            ("files", ("page2.pdf", b"fake pdf 2", "application/pdf")),
        ]
        response = client.post("/v1/builds/test-build-id/pages/batch", files=files)

    assert response.status_code == 200
    result = response.json()
    assert result["buildId"] == "test-build-id"
    assert result["pagesAdded"] == 2
    assert len(result["pages"]) == 2
    assert result["pages"][0]["pageNumber"] == 1
    assert result["pages"][1]["pageNumber"] == 2
    assert "2 pages uploaded successfully" in result["message"]


def test_upload_document_build_pages_batch_single_file(
    document_build_ddb_table, mock_document_build_upload
):
    """Test batch upload with single file uses singular message."""
    with patch("documentai_api.app_build.get_document_build_pages", return_value=[]):
        files = [("files", ("page1.pdf", b"fake pdf", "application/pdf"))]
        response = client.post("/v1/builds/test-build-id/pages/batch", files=files)

    assert response.status_code == 200
    result = response.json()
    assert result["pagesAdded"] == 1
    assert "1 page uploaded successfully" in result["message"]


def test_upload_document_build_pages_batch_invalid_file(
    document_build_ddb_table, mock_document_build_upload
):
    """Test batch upload fails entirely if any file is invalid."""
    mock_document_build_upload["magic"].side_effect = ["application/pdf", "application/zip"]

    files = [
        ("files", ("page1.pdf", b"fake pdf", "application/pdf")),
        ("files", ("page2.zip", b"fake zip", "application/zip")),
    ]
    response = client.post("/v1/builds/test-build-id/pages/batch", files=files)

    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_upload_document_build_pages_batch_continues_numbering(
    document_build_ddb_table, mock_document_build_upload
):
    """Test batch upload continues page numbering from existing pages."""
    existing_pages = [create_page_metadata(1), create_page_metadata(2)]

    with patch("documentai_api.app_build.get_document_build_pages", return_value=existing_pages):
        files = [
            ("files", ("page3.pdf", b"fake pdf", "application/pdf")),
        ]
        response = client.post("/v1/builds/test-build-id/pages/batch", files=files)

    assert response.status_code == 200
    result = response.json()
    assert result["pages"][0]["pageNumber"] == 3


def test_submit_document_build_rollback_on_failure(
    document_build_ddb_table, mock_document_build_submit
):
    """When upload fails after lock acquired, submittedAt is cleared for retry."""
    mock_document_build_submit["get_pages"].return_value = [
        create_page_metadata(1, category="income"),
    ]
    mock_document_build_submit["upload"].side_effect = Exception("S3 exploded")

    with patch("documentai_api.app_build.clear_submitted_at") as mock_clear:
        response = client.post("/v1/builds/test-build-id/submit")

    assert response.status_code == 500
    mock_clear.assert_called_once_with("test-build-id")


def test_upload_document_build_page_max_pages_cap(
    document_build_ddb_table, mock_document_build_upload
):
    """Upload rejects when build already has MAX_PAGES_PER_BUILD pages."""
    from documentai_api.config.constants import MAX_PAGES_PER_BUILD
    from documentai_api.utils.models import PageMetadata

    existing_pages = [
        PageMetadata(
            page_number=i,
            s3_key=f"builds/test-build-id/page-{i}.pdf",
            s3_bucket_name="test-bucket",
        )
        for i in range(1, MAX_PAGES_PER_BUILD + 1)
    ]

    with patch("documentai_api.app_build.get_document_build_pages", return_value=existing_pages):
        files = {"file": ("page.pdf", b"fake pdf", "application/pdf")}
        data = {"page_number": MAX_PAGES_PER_BUILD + 1}
        response = client.post("/v1/builds/test-build-id/pages", files=files, data=data)

    assert response.status_code == 400
    assert "maximum" in response.json()["detail"].lower()


def test_upload_document_build_pages_batch_max_pages_cap(
    document_build_ddb_table, mock_document_build_upload
):
    """Batch upload rejects when total would exceed MAX_PAGES_PER_BUILD."""
    from documentai_api.config.constants import MAX_PAGES_PER_BUILD

    # Cheap pre-check: more files than the cap
    files = [
        ("files", (f"page{i}.pdf", b"fake pdf", "application/pdf"))
        for i in range(MAX_PAGES_PER_BUILD + 1)
    ]
    response = client.post("/v1/builds/test-build-id/pages/batch", files=files)

    assert response.status_code == 400
    assert "maximum" in response.json()["detail"].lower()


def test_submit_document_build_mixed_categories(
    document_build_ddb_table, mock_document_build_submit
):
    """Submit rejects builds with mixed page categories."""
    mock_document_build_submit["get_pages"].return_value = [
        create_page_metadata(1, category="income"),
        create_page_metadata(2, category="identity"),
    ]

    response = client.post("/v1/builds/test-build-id/submit")

    assert response.status_code == 400
    assert "mixed categories" in response.json()["detail"].lower()
    # Verify we didn't acquire the lock
    mock_document_build_submit["mark_submitted"].assert_not_called()


def test_submit_document_build_category_with_none_pages(
    document_build_ddb_table, mock_document_build_submit
):
    """Submit succeeds when some pages have no category and others share one."""
    mock_document_build_submit["get_pages"].return_value = [
        create_page_metadata(1, category="income"),
        create_page_metadata(2, category=None),
    ]

    response = client.post("/v1/builds/test-build-id/submit")

    assert response.status_code == 200


def test_upload_document_build_page_file_size_cap(
    document_build_ddb_table, mock_document_build_upload
):
    """Upload rejects files exceeding MAX_FILE_SIZE_BYTES."""
    files = {"file": ("big.pdf", b"x" * 100, "application/pdf")}
    data = {"page_number": 1}

    # Mock file.size to exceed the cap
    with patch("documentai_api.app_build.MAX_FILE_SIZE_BYTES", 50):
        response = client.post("/v1/builds/test-build-id/pages", files=files, data=data)

    assert response.status_code == 400
    assert "maximum" in response.json()["detail"].lower()


def test_submit_document_build_env_check_before_lock(
    document_build_ddb_table, mock_document_build_submit
):
    """When DOCUMENTAI_INPUT_LOCATION is unset, 500 is returned without acquiring the lock."""
    mock_document_build_submit["get_pages"].return_value = [
        create_page_metadata(1, category="income"),
    ]
    mock_document_build_submit["aws_config"].return_value.documentai_input_location = None

    response = client.post("/v1/builds/test-build-id/submit")

    assert response.status_code == 500
    assert "environment variable" in response.json()["detail"].lower()
    # Lock was NOT acquired
    mock_document_build_submit["mark_submitted"].assert_not_called()


def test_batch_upload_overwrite_false_409(document_build_ddb_table, mock_document_build_upload):
    """Batch upload surfaces 409 when conditional write fails (page already exists)."""
    mock_document_build_upload["upsert"].side_effect = HTTPException(
        status_code=409,
        detail="Page 1 already exists for build test-build-id. Set overwrite=true to replace.",
    )

    with patch("documentai_api.app_build.get_document_build_pages", return_value=[]):
        files = [("files", ("page1.pdf", b"fake pdf", "application/pdf"))]
        response = client.post("/v1/builds/test-build-id/pages/batch", files=files)

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_submit_category_substitution_picks_first_non_none(
    document_build_ddb_table, mock_document_build_submit
):
    """When page 1 has no category but page 2 does, submit uses page 2's category."""
    from documentai_api.config.constants import DocumentCategory

    mock_document_build_submit["get_pages"].return_value = [
        create_page_metadata(1, category=None),
        create_page_metadata(2, category="income"),
    ]

    response = client.post("/v1/builds/test-build-id/submit")

    assert response.status_code == 200
    call_kwargs = mock_document_build_submit["upload"].call_args.kwargs
    assert call_kwargs["user_provided_document_category"] == DocumentCategory.INCOME


def test_upload_document_build_page_number_validation(document_build_ddb_table):
    """page_number=0 is rejected by Form(ge=1) validation."""
    files = {"file": ("page.pdf", b"fake pdf", "application/pdf")}
    data = {"page_number": 0}
    response = client.post("/v1/builds/test-build-id/pages", files=files, data=data)

    assert response.status_code == 422


def test_submit_document_build_timeout_validation(document_build_ddb_table):
    """timeout=999 is rejected by Query(ge=1, le=300) validation."""
    response = client.post("/v1/builds/test-build-id/submit?timeout=999")

    assert response.status_code == 422


def test_upload_document_build_page_image_conversion_error(
    document_build_ddb_table, mock_document_build_upload
):
    """ImageConversionError from upload is converted to 400."""
    mock_document_build_upload["upload"].side_effect = ImageConversionError("HEIC failed")

    files = {"file": ("page.heic", b"fake heic", "image/heic")}
    data = {"page_number": 1}
    response = client.post("/v1/builds/test-build-id/pages", files=files, data=data)

    assert response.status_code == 400
    assert "image conversion failed" in response.json()["detail"].lower()


def test_batch_upload_image_conversion_error(document_build_ddb_table, mock_document_build_upload):
    """ImageConversionError in batch is converted to 400 via TaskGroup except*."""
    mock_document_build_upload["upload"].side_effect = ImageConversionError("PNG conversion failed")

    with patch("documentai_api.app_build.get_document_build_pages", return_value=[]):
        files = [("files", ("page1.png", b"fake png", "image/png"))]
        response = client.post("/v1/builds/test-build-id/pages/batch", files=files)

    assert response.status_code == 400
    assert "image conversion failed" in response.json()["detail"].lower()


def test_upload_document_build_page_trace_id_echoed(
    document_build_ddb_table, mock_document_build_upload
):
    """Client-supplied X-Trace-ID is echoed in response."""
    files = {"file": ("page.pdf", b"fake pdf", "application/pdf")}
    data = {"page_number": 1}
    response = client.post(
        "/v1/builds/test-build-id/pages",
        files=files,
        data=data,
        headers={"X-Trace-ID": "my-trace-123"},
    )

    assert response.status_code == 200
    assert response.headers.get("X-Trace-ID") == "my-trace-123"


def test_upload_document_build_page_trace_id_generated(
    document_build_ddb_table, mock_document_build_upload
):
    """X-Trace-ID is generated when not supplied."""
    import uuid

    files = {"file": ("page.pdf", b"fake pdf", "application/pdf")}
    data = {"page_number": 1}
    response = client.post("/v1/builds/test-build-id/pages", files=files, data=data)

    assert response.status_code == 200
    trace_id = response.headers.get("X-Trace-ID")
    assert trace_id is not None
    uuid.UUID(trace_id)  # valid UUID


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/v1/builds/test-build-id"),
        ("POST", "/v1/builds/test-build-id/pages"),
        ("POST", "/v1/builds/test-build-id/pages/batch"),
        ("POST", "/v1/builds/test-build-id/submit"),
        ("DELETE", "/v1/builds/test-build-id"),
        ("DELETE", "/v1/builds/test-build-id/pages/1"),
    ],
)
def test_tenant_access_enforced_on_all_build_routes(method, path, document_build_ddb_table):
    """All build endpoints with {build_id} enforce tenant access via dependency."""
    from fastapi.testclient import TestClient

    from documentai_api.app import app
    from documentai_api.utils.auth import UserContext, get_user_context
    from documentai_api.utils.tenant import validate_build_tenant_access

    mock_context = UserContext(tenant_id="any-tenant", client_name="test-client")
    called = []

    def _reject_tenant():
        called.append(True)
        raise HTTPException(status_code=404, detail="Not found")

    saved = dict(app.dependency_overrides)
    try:
        app.dependency_overrides[get_user_context] = lambda: mock_context
        app.dependency_overrides[validate_build_tenant_access] = _reject_tenant

        test_client = TestClient(app)
        response = test_client.request(method, path)

        assert response.status_code == 404, f"{method} {path} returned {response.status_code}"
        assert called, f"validate_build_tenant_access was not called for {method} {path}"
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


def test_batch_upload_file_size_cap(document_build_ddb_table, mock_document_build_upload):
    """Batch upload rejects files exceeding MAX_FILE_SIZE_BYTES with filename in error."""
    with (
        patch("documentai_api.app_build.MAX_FILE_SIZE_BYTES", 50),
        patch("documentai_api.app_build.get_document_build_pages", return_value=[]),
    ):
        files = [("files", ("big_doc.pdf", b"x" * 100, "application/pdf"))]
        response = client.post("/v1/builds/test-build-id/pages/batch", files=files)

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "maximum" in detail.lower()
    assert "big_doc.pdf" in detail


@pytest.mark.parametrize("page_number", [0, -1, -100])
def test_upload_document_build_page_number_lower_bound(document_build_ddb_table, page_number):
    """page_number below 1 is rejected by Form(ge=1)."""
    files = {"file": ("page.pdf", b"fake pdf", "application/pdf")}
    data = {"page_number": page_number}
    response = client.post("/v1/builds/test-build-id/pages", files=files, data=data)

    assert response.status_code == 422


@pytest.mark.parametrize("timeout", [0, -1, 301, 999])
def test_submit_document_build_timeout_bounds(document_build_ddb_table, timeout):
    """Timeout outside [1, 300] is rejected by Query(ge=1, le=300)."""
    response = client.post(f"/v1/builds/test-build-id/submit?timeout={timeout}")

    assert response.status_code == 422


def test_create_build_trace_id_echoed(document_build_ddb_table):
    """create_build echoes client-supplied X-Trace-ID."""
    with patch("documentai_api.app_build.create_document_build"):
        response = client.post("/v1/builds", headers={"X-Trace-ID": "trace-create"})

    assert response.status_code == 200
    assert response.headers.get("X-Trace-ID") == "trace-create"


def test_create_build_trace_id_generated(document_build_ddb_table):
    """create_build generates X-Trace-ID when not supplied."""
    import uuid

    with patch("documentai_api.app_build.create_document_build"):
        response = client.post("/v1/builds")

    assert response.status_code == 200
    uuid.UUID(response.headers.get("X-Trace-ID"))


def test_batch_upload_trace_id_echoed(document_build_ddb_table, mock_document_build_upload):
    """Batch upload echoes client-supplied X-Trace-ID."""
    with patch("documentai_api.app_build.get_document_build_pages", return_value=[]):
        files = [("files", ("page1.pdf", b"fake pdf", "application/pdf"))]
        response = client.post(
            "/v1/builds/test-build-id/pages/batch",
            files=files,
            headers={"X-Trace-ID": "trace-batch"},
        )

    assert response.status_code == 200
    assert response.headers.get("X-Trace-ID") == "trace-batch"


def test_submit_trace_id_echoed(document_build_ddb_table, mock_document_build_submit):
    """Submit echoes client-supplied X-Trace-ID."""
    mock_document_build_submit["get_pages"].return_value = [
        create_page_metadata(1, category="income"),
    ]

    response = client.post(
        "/v1/builds/test-build-id/submit", headers={"X-Trace-ID": "trace-submit"}
    )

    assert response.status_code == 200
    assert response.headers.get("X-Trace-ID") == "trace-submit"


@pytest.mark.parametrize(
    ("content_type", "expected_ext"),
    [
        ("image/jpeg", "jpg"),
        ("image/png", "png"),
        ("image/tiff", "tiff"),
    ],
)
def test_upload_document_build_page_non_pdf_content_types(
    document_build_ddb_table, mock_document_build_upload, content_type, expected_ext
):
    """Non-PDF content types flow through successfully with correct extension."""
    mock_document_build_upload["magic"].return_value = content_type

    files = {"file": (f"page.{expected_ext}", b"fake image", content_type)}
    data = {"page_number": 1}
    response = client.post("/v1/builds/test-build-id/pages", files=files, data=data)

    assert response.status_code == 200
    # Verify the upload was called with the correct content type
    call_kwargs = mock_document_build_upload["upload"].call_args.kwargs
    assert call_kwargs["content_type"] == content_type
    # Verify dest_path uses the correct extension
    assert call_kwargs["dest_path"].endswith(f".{expected_ext}")


def test_batch_upload_with_category(document_build_ddb_table, mock_document_build_upload):
    """Batch upload passes category to add_page_to_build."""
    with patch("documentai_api.app_build.get_document_build_pages", return_value=[]):
        files = [("files", ("page1.pdf", b"fake pdf", "application/pdf"))]
        data = {"category": "income"}
        response = client.post("/v1/builds/test-build-id/pages/batch", files=files, data=data)

    assert response.status_code == 200
    # Verify upsert was called with the category
    call_kwargs = mock_document_build_upload["upsert"].call_args.kwargs
    from documentai_api.config.constants import DocumentCategory

    assert call_kwargs["category"] == DocumentCategory.INCOME


def test_submit_document_build_rollback_failure_still_returns_500(
    document_build_ddb_table, mock_document_build_submit
):
    """When upload fails and clear_submitted_at also fails, original 500 still surfaces."""
    mock_document_build_submit["get_pages"].return_value = [
        create_page_metadata(1, category="income"),
    ]
    mock_document_build_submit["upload"].side_effect = Exception("S3 exploded")

    with patch("documentai_api.app_build.clear_submitted_at") as mock_clear:
        mock_clear.side_effect = Exception("DDB unavailable")
        response = client.post("/v1/builds/test-build-id/submit")

    assert response.status_code == 500
    assert "Failed to submit" in response.json()["detail"]
    mock_clear.assert_called_once_with("test-build-id")
