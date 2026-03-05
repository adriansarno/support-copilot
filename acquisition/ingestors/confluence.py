"""Ingest Confluence HTML/XML space exports."""

from __future__ import annotations

import hashlib
from pathlib import Path

from bs4 import BeautifulSoup

from acquisition.ingestors.pdf import Document


class ConfluenceIngestor:
    """Parse a Confluence HTML space export (unzipped directory).

    Confluence exports contain an ``index.html`` manifest and individual
    page HTML files. This ingestor walks every ``.html`` file in the
    export, skips the index, and extracts clean article text.
    """

    SKIP_FILES = {"index.html", "index-toc.html"}

    def ingest_dir(self, directory: Path) -> list[Document]:
        docs: list[Document] = []
        for html_path in sorted(directory.rglob("*.html")):
            if html_path.name in self.SKIP_FILES:
                continue
            docs.append(self._parse_page(html_path))
        return docs

    def _parse_page(self, path: Path) -> Document:
        raw = path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(raw, "lxml")

        for tag in soup.find_all(["script", "style"]):
            tag.decompose()

        title_el = soup.find("title")
        title = title_el.get_text(strip=True) if title_el else path.stem

        content_div = (
            soup.find("div", {"id": "main-content"})
            or soup.find("div", {"class": "wiki-content"})
            or soup.find("body")
            or soup
        )
        text = content_div.get_text(separator="\n", strip=True)

        space_key = ""
        meta_space = soup.find("meta", {"name": "confluence-space-key"})
        if meta_space:
            space_key = meta_space.get("content", "")

        doc_id = hashlib.sha256(str(path).encode()).hexdigest()[:16]

        return Document(
            doc_id=doc_id,
            title=title,
            content=text,
            source_type="confluence",
            metadata={
                "file_path": str(path),
                "space_key": space_key,
            },
        )
