from datetime import UTC, datetime

import pytest

from documentai_api.schemas.document_builds import DocumentBuilds
from documentai_api.utils import document_build as build_util


def _assert_ttl_30_days(item):
    """Build records carry an integer `ttl` epoch ~30 days out."""
    ttl = item[DocumentBuilds.TIME_TO_LIVE]
    expected = int(datetime.now(UTC).timestamp()) + 30 * 24 * 60 * 60
    assert abs(int(ttl) - expected) < 600  # within 10 minutes


def test_create_document_build_stamps_ttl(document_build_ddb_table):
    """create_document_build writes a ttl on the build metadata record (page 0)."""
    build_util.create_document_build("build-ttl-1")

    item = document_build_ddb_table.get_item(
        Key={DocumentBuilds.BUILD_ID: "build-ttl-1", DocumentBuilds.PAGE_NUMBER: 0}
    )["Item"]
    _assert_ttl_30_days(item)


@pytest.mark.asyncio
async def test_upsert_document_build_page_stamps_ttl(document_build_ddb_table):
    """upsert_document_build_page writes a ttl on each page record."""
    await build_util.upsert_document_build_page(
        build_id="build-ttl-2",
        page_number=1,
        s3_path="builds/build-ttl-2/page-1.pdf",
    )

    item = document_build_ddb_table.get_item(
        Key={DocumentBuilds.BUILD_ID: "build-ttl-2", DocumentBuilds.PAGE_NUMBER: 1}
    )["Item"]
    _assert_ttl_30_days(item)
