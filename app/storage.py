"""Filesystem storage services for uploaded documents."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

_SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(filename: str) -> str:
    """Normalize user-provided file names into safe filesystem names.

    Args:
        filename: Original user filename.

    Returns:
        str: Sanitized filename preserving extension when possible.
    """

    cleaned = _SAFE_NAME_PATTERN.sub("_", filename.strip())
    return cleaned or "document.bin"


def allocate_target_path(archive_root: Path, entry_date: date, original_name: str) -> Path:
    """Allocate a deterministic storage path by year/month hierarchy.

    Args:
        archive_root: Root archive folder.
        entry_date: Document registry date.
        original_name: Original uploaded file name.

    Returns:
        Path: Full target path for persistent storage.
    """

    year_folder = archive_root / f"{entry_date.year:04d}"
    month_folder = year_folder / f"{entry_date.month:02d}"
    month_folder.mkdir(parents=True, exist_ok=True)

    safe_name = sanitize_filename(original_name)
    stem = Path(safe_name).stem[:80] or "document"
    suffix = Path(safe_name).suffix.lower()[:16]
    unique_name = f"{stem}_{uuid4().hex}{suffix}"
    return month_folder / unique_name


async def save_upload_streaming(upload: UploadFile, target_path: Path, chunk_size: int) -> int:
    """Persist uploaded content to disk using streaming writes.

    Args:
        upload: FastAPI uploaded file object.
        target_path: Final path for persisted data.
        chunk_size: Number of bytes read per iteration.

    Returns:
        int: Number of bytes written to disk.

    Raises:
        OSError: If file write fails.
    """

    bytes_written = 0
    with target_path.open("wb") as destination:
        while True:
            chunk = await upload.read(chunk_size)
            if not chunk:
                break
            destination.write(chunk)
            bytes_written += len(chunk)

    await upload.close()
    return bytes_written
