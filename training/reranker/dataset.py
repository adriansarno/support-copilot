"""Build (query, positive_doc, negative_doc) triples for cross-encoder training."""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path

from google.cloud import bigquery

logger = logging.getLogger(__name__)


def build_reranker_dataset(
    project: str,
    dataset: str,
    table: str,
    output_path: Path,
    *,
    max_triples: int = 10000,
    val_ratio: float = 0.1,
) -> dict:
    """Generate training triples from ticket data.

    Positive pairs: ticket question + its resolution (same document).
    Negative pairs: ticket question + a random chunk from a different document.
    """
    client = bigquery.Client(project=project)

    sql = f"""
    SELECT chunk_id, doc_id, title, content, source_type
    FROM `{project}.{dataset}.{table}`
    LIMIT {max_triples * 3}
    """
    rows = list(client.query(sql).result())
    logger.info("Fetched %d chunks for reranker dataset", len(rows))

    ticket_chunks = [r for r in rows if r.source_type == "ticket"]
    all_chunks = rows

    triples: list[dict] = []
    for tc in ticket_chunks:
        content = tc.content or ""
        if "Customer:" not in content or "Resolution:" not in content:
            continue

        parts = content.split("Resolution:")
        query = parts[0].replace("Subject:", "").replace("Customer:", "").strip()
        positive = parts[1].strip()

        if len(query) < 20 or len(positive) < 20:
            continue

        neg_candidates = [c for c in all_chunks if c.doc_id != tc.doc_id]
        if not neg_candidates:
            continue
        negative_chunk = random.choice(neg_candidates)

        triples.append({
            "query": query[:500],
            "positive": positive[:500],
            "negative": negative_chunk.content[:500],
        })

        if len(triples) >= max_triples:
            break

    random.shuffle(triples)
    split_idx = int(len(triples) * (1 - val_ratio))
    train = triples[:split_idx]
    val = triples[split_idx:]

    output_path.mkdir(parents=True, exist_ok=True)
    _write_jsonl(train, output_path / "train.jsonl")
    _write_jsonl(val, output_path / "val.jsonl")

    stats = {
        "total_triples": len(triples),
        "train_size": len(train),
        "val_size": len(val),
    }
    logger.info("Reranker dataset built: %s", stats)
    return stats


def _write_jsonl(records: list[dict], path: Path) -> None:
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
