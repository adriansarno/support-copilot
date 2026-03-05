"""Recursive character text splitter wrapping LangChain."""

from __future__ import annotations

from dataclasses import dataclass, field

from langchain_text_splitters import RecursiveCharacterTextSplitter

from acquisition.ingestors.pdf import Document


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    content: str
    source_type: str
    metadata: dict = field(default_factory=dict)
    index: int = 0


class RecursiveChunker:
    """Split documents using LangChain RecursiveCharacterTextSplitter."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def chunk(self, doc: Document) -> list[Chunk]:
        text_chunks = self._splitter.create_documents([doc.content])
        chunks: list[Chunk] = []
        for i, tc in enumerate(text_chunks):
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}_{i:04d}",
                    doc_id=doc.doc_id,
                    title=doc.title,
                    content=tc.page_content,
                    source_type=doc.source_type,
                    metadata={**doc.metadata, "chunk_index": i},
                    index=i,
                )
            )
        return chunks

    def chunk_many(self, docs: list[Document]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for doc in docs:
            chunks.extend(self.chunk(doc))
        return chunks
