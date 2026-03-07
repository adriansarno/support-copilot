"""GCS ingestor: stream objects from gs://bucket/path into the acquisition pipeline."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from google.cloud import storage

from acquisition.ingestors.pdf import Document, PDFIngestor
from acquisition.ingestors.html import HTMLIngestor

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".html", ".htm"}


def parse_gs_url(url: str) -> tuple[str, str]:
    """Parse gs://bucket/path into (bucket, prefix)."""
    if not url.startswith("gs://"):
        raise ValueError(f"Expected gs:// URL, got {url}")
    rest = url[5:]  # strip gs://
    if "/" in rest:
        bucket, prefix = rest.split("/", 1)
        prefix = prefix.rstrip("/") + "/" if prefix else ""
    else:
        bucket, prefix = rest, ""
    return bucket, prefix


class GCSIngestor:
    """Stream objects from GCS into Documents using existing PDF/HTML ingestors."""

    def __init__(self):
        self.pdf_ingestor = PDFIngestor()
        self.html_ingestor = HTMLIngestor()

    def ingest(self, gs_url: str) -> list[Document]:
        """List blobs under gs_url, download to temp, ingest, return Documents."""
        bucket_name, prefix = parse_gs_url(gs_url)
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix=prefix))

        docs: list[Document] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for blob in blobs:
                if blob.name.endswith("/"):
                    continue
                path = Path(blob.name)
                ext = path.suffix.lower()
                if ext not in ALLOWED_EXTENSIONS:
                    logger.debug("Skipping %s (unsupported extension)", blob.name)
                    continue

                # Use sanitized blob path to avoid collisions when multiple files share a name
                safe_name = blob.name.replace("/", "_")
                local_path = tmp / safe_name
                blob.download_to_filename(str(local_path))

                if ext == ".pdf":
                    doc = self.pdf_ingestor.ingest_file(local_path)
                else:
                    doc = self.html_ingestor.ingest_file(local_path)
                doc.metadata["file_path"] = f"gs://{bucket_name}/{blob.name}"
                docs.append(doc)

        logger.info("Ingested %d documents from gs://%s/%s", len(docs), bucket_name, prefix)
        return docs
