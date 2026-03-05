"""Build Q&A pairs from past tickets + docs for answer-style fine-tuning."""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path

from google.cloud import bigquery

logger = logging.getLogger(__name__)


def build_qa_dataset(
    project: str,
    dataset: str,
    table: str,
    output_path: Path,
    *,
    max_samples: int = 5000,
    val_ratio: float = 0.1,
) -> dict:
    """Extract Q&A pairs from ticket data in BigQuery.

    Tickets with both a body (question) and resolution (answer) form
    natural training pairs for answer-style fine-tuning.
    """
    client = bigquery.Client(project=project)

    sql = f"""
    SELECT chunk_id, title, content, source_type, metadata
    FROM `{project}.{dataset}.{table}`
    WHERE source_type = 'ticket'
      AND JSON_VALUE(metadata, '$.ticket_id') IS NOT NULL
    LIMIT {max_samples * 2}
    """
    rows = list(client.query(sql).result())
    logger.info("Fetched %d ticket chunks from BigQuery", len(rows))

    pairs: list[dict] = []
    for row in rows:
        content = row.content or ""
        if "Customer:" in content and "Resolution:" in content:
            parts = content.split("Resolution:")
            question_part = parts[0].replace("Subject:", "").replace("Customer:", "").strip()
            answer_part = parts[1].strip()

            if len(question_part) > 20 and len(answer_part) > 20:
                pairs.append({
                    "instruction": "You are a helpful customer support agent. Answer the customer's question based on company knowledge.",
                    "input": question_part[:1000],
                    "output": answer_part[:2000],
                    "source_chunk_id": row.chunk_id,
                })

    random.shuffle(pairs)
    pairs = pairs[:max_samples]

    split_idx = int(len(pairs) * (1 - val_ratio))
    train = pairs[:split_idx]
    val = pairs[split_idx:]

    output_path.mkdir(parents=True, exist_ok=True)
    train_path = output_path / "train.jsonl"
    val_path = output_path / "val.jsonl"

    _write_jsonl(train, train_path)
    _write_jsonl(val, val_path)

    stats = {
        "total_pairs": len(pairs),
        "train_size": len(train),
        "val_size": len(val),
        "train_path": str(train_path),
        "val_path": str(val_path),
    }
    logger.info("Dataset built: %s", stats)
    return stats


def _write_jsonl(records: list[dict], path: Path) -> None:
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
