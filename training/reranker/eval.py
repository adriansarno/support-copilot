"""Evaluate reranker with nDCG and MRR metrics."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
from datasets import load_dataset
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


def evaluate_reranker(
    model_path: str,
    val_path: Path,
    *,
    output_path: Path | None = None,
) -> dict:
    """Compute nDCG@k and MRR on the validation set."""
    model = CrossEncoder(model_path)
    val_ds = load_dataset("json", data_files=str(val_path), split="train")

    queries: dict[str, list[tuple[str, float]]] = {}
    for row in val_ds:
        q = row["query"]
        if q not in queries:
            queries[q] = []
        queries[q].append((row["positive"], 1.0))
        queries[q].append((row["negative"], 0.0))

    ndcg_scores: list[float] = []
    mrr_scores: list[float] = []

    for query, docs in queries.items():
        doc_texts = [d[0] for d in docs]
        true_relevance = [d[1] for d in docs]

        pairs = [(query, d) for d in doc_texts]
        pred_scores = model.predict(pairs)

        ranked_indices = np.argsort(-np.array(pred_scores))
        ranked_rel = [true_relevance[i] for i in ranked_indices]

        ndcg_scores.append(_ndcg_at_k(ranked_rel, k=10))

        for rank, rel in enumerate(ranked_rel, start=1):
            if rel > 0:
                mrr_scores.append(1.0 / rank)
                break
        else:
            mrr_scores.append(0.0)

    metrics = {
        "ndcg@10": float(np.mean(ndcg_scores)),
        "mrr": float(np.mean(mrr_scores)),
        "num_queries": len(queries),
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(metrics, f, indent=2)

    logger.info("Reranker eval: nDCG@10=%.4f MRR=%.4f", metrics["ndcg@10"], metrics["mrr"])
    return metrics


def _ndcg_at_k(ranked_relevance: list[float], k: int = 10) -> float:
    """Compute normalized discounted cumulative gain at k."""
    rel = np.array(ranked_relevance[:k])
    dcg = np.sum(rel / np.log2(np.arange(2, len(rel) + 2)))

    ideal = np.sort(np.array(ranked_relevance))[::-1][:k]
    idcg = np.sum(ideal / np.log2(np.arange(2, len(ideal) + 2)))

    return float(dcg / idcg) if idcg > 0 else 0.0
