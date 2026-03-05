"""Ingest PDF files using PyMuPDF and extract structured text."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class Document:
    doc_id: str
    title: str
    content: str
    source_type: str
    metadata: dict = field(default_factory=dict)


class PDFIngestor:
    """Extract text from PDF files, one Document per file."""

    def ingest_file(self, path: Path) -> Document:
        doc = fitz.open(str(path))
        pages: list[str] = []
        for page in doc:
            pages.append(page.get_text("text"))
        doc.close()

        full_text = "\n\n".join(pages)
        doc_id = hashlib.sha256(str(path).encode()).hexdigest()[:16]

        return Document(
            doc_id=doc_id,
            title=path.stem,
            content=full_text,
            source_type="pdf",
            metadata={
                "file_path": str(path),
                "page_count": len(pages),
            },
        )

    def ingest_dir(self, directory: Path) -> list[Document]:
        docs: list[Document] = []
        for pdf_path in sorted(directory.rglob("*.pdf")):
            docs.append(self.ingest_file(pdf_path))
        return docs
