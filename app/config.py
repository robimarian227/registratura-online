"""Application configuration primitives for the digital registry."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables.

    Attributes:
        app_name: Human-readable application name.
        db_path: Path to the SQLite database file.
        archive_root: Root folder where documents are persisted.
        upload_chunk_bytes: Stream chunk size used for file upload.
        large_file_threshold_bytes: Threshold used to classify large files.
    """

    app_name: str
    db_path: Path
    archive_root: Path
    upload_chunk_bytes: int
    large_file_threshold_bytes: int


def load_settings() -> Settings:
    """Load runtime settings and create required directories.

    Returns:
        Settings: Fully validated settings object.

    Raises:
        ValueError: If chunk size or threshold values are invalid.
    """

    app_name = os.getenv("REGISTRY_APP_NAME", "Registratura Digitala Interna")
    db_path = Path(os.getenv("REGISTRY_DB_PATH", "data/registry.db")).expanduser()
    archive_root = Path(
        os.getenv("REGISTRY_ARCHIVE_ROOT", "D:/Registratura_Archive")
    ).expanduser()

    upload_chunk_bytes = int(os.getenv("REGISTRY_UPLOAD_CHUNK_BYTES", str(4 * 1024 * 1024)))
    large_file_threshold_bytes = int(
        os.getenv("REGISTRY_LARGE_FILE_THRESHOLD", str(100 * 1024 * 1024))
    )

    if upload_chunk_bytes <= 0:
        raise ValueError("REGISTRY_UPLOAD_CHUNK_BYTES must be a positive integer")
    if large_file_threshold_bytes <= 0:
        raise ValueError("REGISTRY_LARGE_FILE_THRESHOLD must be a positive integer")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    archive_root.mkdir(parents=True, exist_ok=True)

    return Settings(
        app_name=app_name,
        db_path=db_path,
        archive_root=archive_root,
        upload_chunk_bytes=upload_chunk_bytes,
        large_file_threshold_bytes=large_file_threshold_bytes,
    )
