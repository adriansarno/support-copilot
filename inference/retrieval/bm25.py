"""BM25 retrieval via BigQuery SEARCH() function."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from google.cloud import bigquery

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    title: str
    content: str
    source_type: str
    score: float = 0.0
    metadata: dict = field(default_factory=dict)


class BM25Retriever:
    """Full-text search over BigQuery chunks table using SEARCH()."""

    def __init__(self, project: str, dataset: str, table: str):
        self._client = bigquery.Client(project=project)
        self._table_id = f"{project}.{dataset}.{table}"

    def search(
        self, query: str, top_k: int = 20, source_type: str | None = None
    ) -> list[RetrievedChunk]:
        where_clause = ""
        if source_type:
            where_clause = f"AND source_type = '{source_type}'"

        sql = f"""
        SELECT
            chunk_id, doc_id, title, content, source_type, metadata,
            SEARCH_SCORE(content) AS score
        FROM `{self._table_id}`
        WHERE SEARCH(content, @query)
        {where_clause}
        ORDER BY score DESC
        LIMIT @top_k
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("query", "STRING", query),
                bigquery.ScalarQueryParameter("top_k", "INT64", top_k),
            ]
        )

        results = self._client.query(sql, job_config=job_config).result()

        chunks: list[RetrievedChunk] = []
        for row in results:
            chunks.append(
                RetrievedChunk(
                    chunk_id=row.chunk_id,
                    doc_id=row.doc_id,
                    title=row.title,
                    content=row.content,
                    source_type=row.source_type,
                    score=float(row.score),
                    metadata=row.metadata if row.metadata else {},
                )
            )

        logger.info("BM25 search returned %d results for: %s", len(chunks), query[:80])
        return chunks
