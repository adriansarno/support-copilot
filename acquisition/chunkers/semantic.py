"""Semantic chunker: split on embedding-similarity boundaries."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from acquisition.ingestors.pdf import Document
from acquisition.chunkers.recursive import Chunk


class SemanticChunker:
    """Split text into chunks at semantic breakpoints.

    Sentences whose consecutive embeddings have cosine distance above a
    threshold are treated as chunk boundaries. Mirrors the approach from
    the cheese-app RAG tutorial's ``semantic_splitter.py``.
    """

    def __init__(
        self,
        embed_fn: Callable[[list[str]], list[list[float]]],
        *,
        buffer_size: int = 1,
        percentile_threshold: float = 95.0,
        min_chunk_chars: int = 100,
    ):
        self._embed_fn = embed_fn
        self._buffer_size = buffer_size
        self._percentile_threshold = percentile_threshold
        self._min_chunk_chars = min_chunk_chars

    def chunk(self, doc: Document) -> list[Chunk]:
        sentences = self._split_sentences(doc.content)
        if len(sentences) <= 1:
            return [
                Chunk(
                    chunk_id=f"{doc.doc_id}_0000",
                    doc_id=doc.doc_id,
                    title=doc.title,
                    content=doc.content,
                    source_type=doc.source_type,
                    metadata={**doc.metadata, "chunk_index": 0},
                    index=0,
                )
            ]

        combined = self._combine_with_buffer(sentences)
        embeddings = self._embed_fn(combined)
        distances = self._cosine_distances(embeddings)

        threshold = float(np.percentile(distances, self._percentile_threshold))
        breakpoints = [i for i, d in enumerate(distances) if d > threshold]

        groups: list[str] = []
        start = 0
        for bp in breakpoints:
            group_text = " ".join(sentences[start : bp + 1])
            if len(group_text) >= self._min_chunk_chars:
                groups.append(group_text)
                start = bp + 1
        tail = " ".join(sentences[start:])
        if tail.strip():
            if groups and len(tail) < self._min_chunk_chars:
                groups[-1] += " " + tail
            else:
                groups.append(tail)

        chunks: list[Chunk] = []
        for i, text in enumerate(groups):
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}_{i:04d}",
                    doc_id=doc.doc_id,
                    title=doc.title,
                    content=text.strip(),
                    source_type=doc.source_type,
                    metadata={**doc.metadata, "chunk_index": i},
                    index=i,
                )
            )
        return chunks

    def chunk_many(self, docs: list[Document]) -> list[Chunk]:
        all_chunks: list[Chunk] = []
        for doc in docs:
            all_chunks.extend(self.chunk(doc))
        return all_chunks

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _combine_with_buffer(self, sentences: list[str]) -> list[str]:
        combined: list[str] = []
        for i in range(len(sentences)):
            start = max(0, i - self._buffer_size)
            end = min(len(sentences), i + self._buffer_size + 1)
            combined.append(" ".join(sentences[start:end]))
        return combined

    @staticmethod
    def _cosine_distances(embeddings: list[list[float]]) -> list[float]:
        arr = np.array(embeddings)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1e-10, norms)
        normed = arr / norms

        distances: list[float] = []
        for i in range(len(normed) - 1):
            sim = float(np.dot(normed[i], normed[i + 1]))
            distances.append(1.0 - sim)
        return distances
