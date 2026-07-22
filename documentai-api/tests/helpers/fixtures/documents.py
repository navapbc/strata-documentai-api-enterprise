import pytest


@pytest.fixture
def blank_pdf_bytes():
    from tests.helpers.documents import generate_blank_pdf

    return generate_blank_pdf()


@pytest.fixture
def blank_pdf_file(blank_pdf_bytes, tmp_path):
    file = tmp_path / "test.pdf"
    file.write_bytes(blank_pdf_bytes)
    return file


@pytest.fixture
def empty_zip_bytes():
    import io
    import zipfile

    zip_file = io.BytesIO()
    with zipfile.ZipFile(zip_file, "w") as _f:
        pass

    yield zip_file.getvalue()

    zip_file.close()


@pytest.fixture
def blank_docx_bytes():
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        )
        z.writestr("word/document.xml", "<w:document/>")
    return buf.getvalue()


@pytest.fixture
def blank_odt_bytes():
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("mimetype", "application/vnd.oasis.opendocument.text")
        z.writestr("content.xml", "<office:document/>")
    return buf.getvalue()


@pytest.fixture
def blank_doc_bytes():
    # OLE2 magic at offset 0, Word FIB signature at offset 512
    data = bytearray(600)
    data[0:8] = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    data[512:516] = b"\xec\xa5\xc1\x00"
    return bytes(data)
