"""Hybrid retrieval: merge BM25 + vector results via Reciprocal Rank Fusion."""

from __future__ import annotations

import logging
from collections import defaultdict

from inference.retrieval.bm25 import RetrievedChunk

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    *result_lists: list[RetrievedChunk],
    k: int = 60,
) -> list[RetrievedChunk]:
    """Merge multiple ranked result lists using RRF.

    RRF score for document d = sum over lists L of  1 / (k + rank_L(d))
    where rank is 1-indexed.
    """
    rrf_scores: dict[str, float] = defaultdict(float)
    chunk_map: dict[str, RetrievedChunk] = {}

    for result_list in result_lists:
        for rank, chunk in enumerate(result_list, start=1):
            rrf_scores[chunk.chunk_id] += 1.0 / (k + rank)
            if chunk.chunk_id not in chunk_map:
                chunk_map[chunk.chunk_id] = chunk

    sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)

    merged: list[RetrievedChunk] = []
    for cid in sorted_ids:
        chunk = chunk_map[cid]
        chunk.score = rrf_scores[cid]
        merged.append(chunk)

    logger.info(
        "RRF merged %d unique chunks from %d lists",
        len(merged),
        len(result_lists),
    )
    return merged


class HybridRetriever:
    """Combine BM25 and vector retrieval with reciprocal rank fusion."""

    def __init__(self, bm25_retriever, vector_retriever, embedding_provider):
        self._bm25 = bm25_retriever
        self._vector = vector_retriever
        self._embed = embedding_provider

    async def search(
        self,
        query: str,
        top_k: int = 20,
        rrf_k: int = 60,
    ) -> list[RetrievedChunk]:
        bm25_results = self._bm25.search(query, top_k=top_k)

        query_embedding = await self._embed.embed_single(query)
        vec_results = await self._vector.search(query_embedding, top_k=top_k)

        fused = reciprocal_rank_fusion(bm25_results, vec_results, k=rrf_k)
        return fused[:top_k]
