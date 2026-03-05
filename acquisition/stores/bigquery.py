"""Write embedded chunks to BigQuery (for both vector + BM25 retrieval)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from google.cloud import bigquery

from acquisition.embedders.embed import EmbeddedChunk

logger = logging.getLogger(__name__)

CHUNKS_SCHEMA = [
    bigquery.SchemaField("chunk_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("doc_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("source_type", "STRING"),
    bigquery.SchemaField("title", "STRING"),
    bigquery.SchemaField("content", "STRING"),
    bigquery.SchemaField("metadata", "JSON"),
    bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
    bigquery.SchemaField("created_at", "TIMESTAMP"),
    bigquery.SchemaField("version", "INT64"),
]


class BigQueryChunkStore:
    """Upsert embedded chunks into a BigQuery table."""

    def __init__(self, project: str, dataset: str, table: str):
        self._client = bigquery.Client(project=project)
        self._table_id = f"{project}.{dataset}.{table}"
        self._dataset_id = f"{project}.{dataset}"

    def ensure_table(self) -> None:
        dataset_ref = bigquery.DatasetReference.from_string(self._dataset_id)
        try:
            self._client.get_dataset(dataset_ref)
        except Exception:
            dataset = bigquery.Dataset(dataset_ref)
            self._client.create_dataset(dataset, exists_ok=True)

        table_ref = bigquery.TableReference.from_string(self._table_id)
        table = bigquery.Table(table_ref, schema=CHUNKS_SCHEMA)

        search_index_sql = f"""
        CREATE SEARCH INDEX IF NOT EXISTS `chunks_search_idx`
        ON `{self._table_id}` (content)
        """
        self._client.create_table(table, exists_ok=True)
        try:
            self._client.query(search_index_sql).result()
        except Exception as e:
            logger.warning("Could not create search index: %s", e)

    def upsert(self, chunks: list[EmbeddedChunk], version: int = 1) -> int:
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            {
                "chunk_id": c.chunk_id,
                "doc_id": c.doc_id,
                "source_type": c.source_type,
                "title": c.title,
                "content": c.content,
                "metadata": json.dumps(c.metadata),
                "embedding": c.embedding,
                "created_at": now,
                "version": version,
            }
            for c in chunks
        ]

        errors = self._client.insert_rows_json(self._table_id, rows)
        if errors:
            logger.error("BigQuery insert errors: %s", errors)
            raise RuntimeError(f"BigQuery insert failed: {errors}")

        logger.info("Inserted %d chunks into %s", len(rows), self._table_id)
        return len(rows)
