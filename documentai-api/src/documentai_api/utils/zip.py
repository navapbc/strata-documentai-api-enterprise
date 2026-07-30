import io
import os
import zipfile

from fastapi import HTTPException, UploadFile

from documentai_api.config.constants import (
    MAX_BATCH_SIZE,
    MAX_ZIP_DECOMPRESSION_RATIO,
    MAX_ZIP_EXTRACTED_BYTES,
)
from documentai_api.logging import get_logger

logger = get_logger(__name__)


async def extract_files_from_zip(
    zip_file: UploadFile, max_files: int = MAX_BATCH_SIZE
) -> list[UploadFile]:
    """Extract files from zip archive and return as UploadFile list.

    Handles nested directories - extracts all files using basename only.
    Enforces max file count and decompression ratio limits during extraction.
    """
    try:
        zip_content = await zip_file.read()
        zip_size = len(zip_content)
        files: list[UploadFile] = []
        total_extracted = 0

        with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
            for file_info in zf.infolist():
                if file_info.is_dir():
                    continue

                if len(files) >= max_files:
                    raise HTTPException(
                        status_code=400,
                        detail=f"ZIP contains more than {max_files} files",
                    )

                # Check the uncompressed size declared in the central directory
                # before decompressing to prevent decompression-bomb allocation.
                # file_info.file_size is the stored uncompressed size; it can be
                # spoofed for stored (method=0) entries but is reliable for deflated
                # entries and provides a fast pre-check before any decompression.
                projected_total = total_extracted + file_info.file_size

                if projected_total > MAX_ZIP_EXTRACTED_BYTES:
                    raise HTTPException(
                        status_code=400,
                        detail="ZIP extracted size exceeds limit",
                    )
                if zip_size > 0 and projected_total / zip_size > MAX_ZIP_DECOMPRESSION_RATIO:
                    raise HTTPException(
                        status_code=400,
                        detail="ZIP decompression ratio exceeds limit",
                    )

                file_content = zf.read(file_info.filename)
                total_extracted += len(file_content)

                # Re-check with actual decompressed size (guards against spoofed headers).
                if total_extracted > MAX_ZIP_EXTRACTED_BYTES:
                    raise HTTPException(
                        status_code=400,
                        detail="ZIP extracted size exceeds limit",
                    )

                if zip_size > 0 and total_extracted / zip_size > MAX_ZIP_DECOMPRESSION_RATIO:
                    raise HTTPException(
                        status_code=400,
                        detail="ZIP decompression ratio exceeds limit",
                    )

                upload_file = UploadFile(
                    filename=os.path.basename(file_info.filename), file=io.BytesIO(file_content)
                )
                files.append(upload_file)

        logger.info(f"Extracted {len(files)} files from {zip_file.filename}")
        return files

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip file") from None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting zip: {e}")
        raise HTTPException(status_code=500, detail="Failed to extract zip file") from e
