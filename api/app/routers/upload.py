"""Document upload endpoint: direct upload to GCS."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from api.app.config import get_api_settings
from api.app.middleware.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_EXTENSIONS = {".pdf", ".html", ".htm"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _get_raw_docs_bucket() -> str:
    settings = get_api_settings()
    if settings.gcs_raw_docs_bucket:
        return settings.gcs_raw_docs_bucket
    if settings.gcp_project:
        return f"{settings.gcp_project}-raw-docs"
    raise ValueError("gcs_raw_docs_bucket or gcp_project must be set")


@router.post("/")
async def upload_documents(
    _key: str = Depends(verify_api_key),
    files: list[UploadFile] = File(..., description="PDF or HTML files to upload"),
):
    """Upload documents to GCS. Files are stored under uploads/{date}/{uuid}_{filename}."""
    from google.cloud import storage

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    try:
        bucket_name = _get_raw_docs_bucket()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    date_prefix = datetime.utcnow().strftime("%Y-%m-%d")
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    uploaded: list[str] = []
    errors: list[str] = []

    for file in files:
        if not file.filename:
            errors.append("Skipped file with no filename")
            continue

        path = Path(file.filename)
        ext = path.suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            errors.append(f"{file.filename}: unsupported type (allowed: .pdf, .html, .htm)")
            continue

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            errors.append(f"{file.filename}: exceeds 10MB limit")
            continue

        blob_name = f"uploads/{date_prefix}/{uuid.uuid4().hex}_{path.name}"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(
            content,
            content_type=file.content_type or "application/octet-stream",
        )
        uploaded.append(blob_name)
        logger.info("Uploaded %s -> gs://%s/%s", file.filename, bucket_name, blob_name)

    if not uploaded and errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    return {
        "uploaded": uploaded,
        "errors": errors,
        "bucket": bucket_name,
        "message": "Documents uploaded. Run ingestion to add them to the knowledge base.",
    }
