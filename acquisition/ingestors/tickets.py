"""Ingest past support tickets from JSON or CSV exports."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from acquisition.ingestors.pdf import Document


class TicketIngestor:
    """Load support tickets from JSON-lines or CSV files.

    Expected JSON-lines schema (one object per line)::

        {"id": "T-1234", "subject": "...", "body": "...", "resolution": "...", "tags": [...]}

    Expected CSV columns: id, subject, body, resolution, tags
    """

    def ingest_file(self, path: Path) -> list[Document]:
        if path.suffix == ".csv":
            return self._load_csv(path)
        return self._load_jsonl(path)

    def ingest_dir(self, directory: Path) -> list[Document]:
        docs: list[Document] = []
        for ext in ("*.jsonl", "*.json", "*.csv"):
            for fpath in sorted(directory.rglob(ext)):
                docs.extend(self.ingest_file(fpath))
        return docs

    def _load_jsonl(self, path: Path) -> list[Document]:
        docs: list[Document] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                docs.append(self._record_to_doc(record, str(path)))
        return docs

    def _load_csv(self, path: Path) -> list[Document]:
        docs: list[Document] = []
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                docs.append(self._record_to_doc(row, str(path)))
        return docs

    @staticmethod
    def _record_to_doc(record: dict, source_path: str) -> Document:
        ticket_id = record.get("id", "")
        subject = record.get("subject", "")
        body = record.get("body", "")
        resolution = record.get("resolution", "")
        tags = record.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        content_parts = []
        if subject:
            content_parts.append(f"Subject: {subject}")
        if body:
            content_parts.append(f"Customer:\n{body}")
        if resolution:
            content_parts.append(f"Resolution:\n{resolution}")

        content = "\n\n".join(content_parts)
        doc_id = (
            ticket_id
            or hashlib.sha256(content.encode()).hexdigest()[:16]
        )

        return Document(
            doc_id=doc_id,
            title=subject or f"Ticket {doc_id}",
            content=content,
            source_type="ticket",
            metadata={
                "file_path": source_path,
                "ticket_id": ticket_id,
                "tags": tags,
            },
        )
