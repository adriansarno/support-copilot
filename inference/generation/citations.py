"""Extract and validate inline citations from LLM responses."""

from __future__ import annotations

import re
from dataclasses import dataclass

from inference.retrieval.bm25 import RetrievedChunk


@dataclass
class Citation:
    source_index: int
    chunk_id: str
    title: str
    source_type: str
    content_snippet: str


class CitationExtractor:
    """Parse [Source N] citations from generated text and map to chunks."""

    PATTERN = re.compile(r"\[Source\s+(\d+)\]")

    def extract(
        self, text: str, chunks: list[RetrievedChunk]
    ) -> tuple[str, list[Citation]]:
        """Return (cleaned_text, citations)."""
        found_indices: set[int] = set()
        for match in self.PATTERN.finditer(text):
            idx = int(match.group(1))
            found_indices.add(idx)

        citations: list[Citation] = []
        for idx in sorted(found_indices):
            if 1 <= idx <= len(chunks):
                chunk = chunks[idx - 1]
                snippet = chunk.content[:200].replace("\n", " ")
                citations.append(
                    Citation(
                        source_index=idx,
                        chunk_id=chunk.chunk_id,
                        title=chunk.title,
                        source_type=chunk.source_type,
                        content_snippet=snippet,
                    )
                )

        return text, citations

    @staticmethod
    def citations_to_dict(citations: list[Citation]) -> list[dict]:
        return [
            {
                "source_index": c.source_index,
                "chunk_id": c.chunk_id,
                "title": c.title,
                "source_type": c.source_type,
                "content_snippet": c.content_snippet,
            }
            for c in citations
        ]
