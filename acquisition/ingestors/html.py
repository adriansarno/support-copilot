"""Ingest HTML files / web pages and extract clean text."""

from __future__ import annotations

import hashlib
from pathlib import Path

from bs4 import BeautifulSoup

from acquisition.ingestors.pdf import Document


class HTMLIngestor:
    """Extract text from HTML files, stripping navigation / boilerplate."""

    STRIP_TAGS = {"script", "style", "nav", "footer", "header", "aside", "form"}

    def ingest_file(self, path: Path) -> Document:
        raw_html = path.read_text(encoding="utf-8", errors="replace")
        return self.ingest_html(raw_html, source_path=str(path), title=path.stem)

    def ingest_html(
        self, html: str, *, source_path: str = "", title: str = ""
    ) -> Document:
        soup = BeautifulSoup(html, "lxml")

        for tag in soup.find_all(self.STRIP_TAGS):
            tag.decompose()

        if not title:
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else "untitled"

        main = soup.find("main") or soup.find("article") or soup.find("body") or soup
        text = main.get_text(separator="\n", strip=True)

        doc_id = hashlib.sha256(
            (source_path or html[:500]).encode()
        ).hexdigest()[:16]

        return Document(
            doc_id=doc_id,
            title=title,
            content=text,
            source_type="html",
            metadata={"file_path": source_path},
        )

    def ingest_dir(self, directory: Path) -> list[Document]:
        docs: list[Document] = []
        for ext in ("*.html", "*.htm"):
            for html_path in sorted(directory.rglob(ext)):
                docs.append(self.ingest_file(html_path))
        return docs
