"""Batch-embed chunks using the shared EmbeddingProvider."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from acquisition.chunkers.recursive import Chunk

logger = logging.getLogger(__name__)


@dataclass
class EmbeddedChunk:
    chunk_id: str
    doc_id: str
    title: str
    content: str
    source_type: str
    embedding: list[float]
    metadata: dict = field(default_factory=dict)


class ChunkEmbedder:
    """Embed a list of Chunks using the shared EmbeddingProvider.

    Accepts either the shared async ``EmbeddingProvider`` or a synchronous
    callable ``(list[str]) -> list[list[float]]`` for testing.
    """

    def __init__(self, provider, *, batch_size: int = 100):
        self._provider = provider
        self._batch_size = batch_size

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        texts = [c.content for c in chunks]
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            logger.info(
                "Embedding batch %d/%d (%d chunks)",
                i // self._batch_size + 1,
                (len(texts) - 1) // self._batch_size + 1,
                len(batch),
            )
            result = await self._provider.embed(batch)
            all_embeddings.extend(result.embeddings)

        embedded: list[EmbeddedChunk] = []
        for chunk, emb in zip(chunks, all_embeddings):
            embedded.append(
                EmbeddedChunk(
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    title=chunk.title,
                    content=chunk.content,
                    source_type=chunk.source_type,
                    embedding=emb,
                    metadata=chunk.metadata,
                )
            )
        return embedded
