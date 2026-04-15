"""FastAPI entrypoint for the Digital Document Registry."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from app.database import Database, DocumentRecord, utc_now_iso
from app.storage import allocate_target_path, save_upload_streaming

settings = load_settings()
app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
repository = Database(settings.db_path)
repository.initialize()


def parse_iso_date(raw_date: str | None) -> date | None:
    """Convert an ISO date string into a date object.

    Args:
        raw_date: Date in YYYY-MM-DD format.

    Returns:
        date | None: Parsed value or None for empty input.

    Raises:
        HTTPException: If date format is invalid.
    """

    if not raw_date:
        return None
    try:
        return date.fromisoformat(raw_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid ISO date: {raw_date}") from exc


@app.get("/")
def root() -> RedirectResponse:
    """Redirect home route to the document list view."""

    return RedirectResponse(url="/documents", status_code=302)


@app.get("/documents")
def list_documents(
    request: Request,
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    sender: str | None = Query(default=None),
    subject: str | None = Query(default=None),
    tag: str | None = Query(default=None),
):
    """Render searchable document list.

    Args:
        request: Active FastAPI request object.
        date_from: Optional lower date bound.
        date_to: Optional upper date bound.
        sender: Optional sender substring.
        subject: Optional subject substring.
        tag: Optional exact tag.
    """

    records = repository.search_documents(
        date_from=parse_iso_date(date_from),
        date_to=parse_iso_date(date_to),
        sender=sender,
        subject=subject,
        tag=tag,
    )

    return templates.TemplateResponse(
        request=request,
        name="documents_list.html",
        context={
            "app_name": settings.app_name,
            "documents": records,
            "filters": {
                "date_from": date_from or "",
                "date_to": date_to or "",
                "sender": sender or "",
                "subject": subject or "",
                "tag": tag or "",
            },
        },
    )


@app.get("/documents/new")
def new_document_form(request: Request):
    """Render upload form for new registry document."""

    return templates.TemplateResponse(
        request=request,
        name="upload_form.html",
        context={
            "app_name": settings.app_name,
            "today": date.today().isoformat(),
            "large_file_threshold_mb": settings.large_file_threshold_bytes // (1024 * 1024),
        },
    )


@app.post("/documents")
async def create_document(
    request: Request,
    entry_date: str = Form(...),
    sender: str = Form(...),
    subject: str = Form(...),
    tags: str = Form(default=""),
    file: UploadFile = File(...),
):
    """Create a document record and store the binary payload in archive storage.

    Args:
        request: Active FastAPI request object.
        entry_date: Registry date in ISO format.
        sender: Sender identity.
        subject: Subject text.
        tags: Comma-separated tags.
        file: Uploaded binary payload.
    """

    parsed_date = parse_iso_date(entry_date)
    if parsed_date is None:
        raise HTTPException(status_code=400, detail="entry_date is required")

    if not sender.strip() or not subject.strip() or not file.filename:
        raise HTTPException(status_code=400, detail="sender, subject and file are mandatory")

    target_path = allocate_target_path(
        archive_root=settings.archive_root,
        entry_date=parsed_date,
        original_name=file.filename,
    )

    bytes_written = await save_upload_streaming(
        upload=file,
        target_path=target_path,
        chunk_size=settings.upload_chunk_bytes,
    )

    record = DocumentRecord(
        document_id=None,
        entry_date=parsed_date,
        sender=sender.strip(),
        subject=subject.strip(),
        file_path=str(target_path),
        original_filename=file.filename,
        file_size=bytes_written,
        tags=[token for token in tags.split(",")],
        created_at=utc_now_iso(),
    )
    repository.insert_document(record)

    return RedirectResponse(url="/documents", status_code=303)


@app.get("/documents/{document_id}/file")
def open_document_file(document_id: int):
    """Serve a stored file by document identifier.

    Args:
        document_id: Stable document identifier.

    Raises:
        HTTPException: If metadata or underlying file path is missing.
    """

    record = repository.get_document_by_id(document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found")

    path = Path(record.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored file is missing")

    return FileResponse(path=path, filename=record.original_filename)
