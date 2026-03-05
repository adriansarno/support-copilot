"""Cross-encoder reranker: score (query, document) pairs and reorder."""

from __future__ import annotations

import logging

from sentence_transformers import CrossEncoder

from inference.retrieval.bm25 import RetrievedChunk

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class CrossEncoderReranker:
    """Load a cross-encoder model and rerank retrieved chunks."""

    def __init__(self, model_name_or_path: str = DEFAULT_MODEL, *, device: str = "cpu"):
        logger.info("Loading cross-encoder: %s", model_name_or_path)
        self._model = CrossEncoder(model_name_or_path, device=device)

    def rerank(
        self, query: str, chunks: list[RetrievedChunk], top_k: int | None = None
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []

        pairs = [(query, c.content) for c in chunks]
        scores = self._model.predict(pairs)

        for chunk, score in zip(chunks, scores):
            chunk.score = float(score)

        ranked = sorted(chunks, key=lambda c: c.score, reverse=True)

        if top_k:
            ranked = ranked[:top_k]

        logger.info(
            "Reranked %d chunks, top score=%.4f, bottom score=%.4f",
            len(ranked),
            ranked[0].score if ranked else 0,
            ranked[-1].score if ranked else 0,
        )
        return ranked
