"""Vector retrieval: BigQuery VECTOR_SEARCH (default) or a Vertex AI Vector Search endpoint."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from google.cloud import aiplatform, bigquery

from inference.retrieval.bm25 import RetrievedChunk

logger = logging.getLogger(__name__)


class BigQueryVectorRetriever:
    """Nearest-neighbour search with BigQuery VECTOR_SEARCH on the chunks table.

    The embeddings are already stored in the table's `embedding` column, so nothing
    else is deployed and nothing costs money while idle. Each query is billed by the
    bytes it reads (BigQuery's 10 MB minimum for a small table). Without a vector
    index BigQuery compares the query with every row, which is fast for a table of
    this size; BigQuery only allows a vector index from 5,000 rows.
    """

    def __init__(self, project: str, bq_dataset: str, bq_table: str):
        self._client = bigquery.Client(project=project)
        self._table_id = f"{project}.{bq_dataset}.{bq_table}"

    def build_sql(self, top_k: int) -> str:
        return f"""
        SELECT base.chunk_id, base.doc_id, base.title, base.content,
               base.source_type, base.metadata, distance
        FROM VECTOR_SEARCH(
            TABLE `{self._table_id}`, 'embedding',
            (SELECT @query_embedding AS embedding),
            top_k => {int(top_k)}, distance_type => 'COSINE')
        ORDER BY distance
        """

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 20,
    ) -> list[RetrievedChunk]:
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("query_embedding", "FLOAT64", query_embedding)
            ]
        )
        rows = self._client.query(self.build_sql(top_k), job_config=job_config).result()
        chunks = [
            RetrievedChunk(
                chunk_id=row.chunk_id,
                doc_id=row.doc_id,
                title=row.title,
                content=row.content,
                source_type=row.source_type,
                # Cosine distance is 0 for the same direction; the score is the similarity.
                score=1.0 - float(row.distance),
                metadata=row.metadata if row.metadata else {},
            )
            for row in rows
        ]
        logger.info("BigQuery vector search returned %d results", len(chunks))
        return chunks


class VectorRetriever:
    """Query a deployed Vertex Vector Search index endpoint, then hydrate
    chunk metadata from BigQuery.
    """

    def __init__(
        self,
        project: str,
        region: str,
        index_endpoint_id: str,
        deployed_index_id: str,
        bq_dataset: str,
        bq_table: str,
    ):
        self._project = project
        self._region = region
        self._bq_table = f"{project}.{bq_dataset}.{bq_table}"
        aiplatform.init(project=project, location=region)
        self._endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_id)
        self._deployed_index_id = deployed_index_id
        self._bq_client = bigquery.Client(project=project)

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 20,
    ) -> list[RetrievedChunk]:
        response = self._endpoint.find_neighbors(
            deployed_index_id=self._deployed_index_id,
            queries=[query_embedding],
            num_neighbors=top_k,
        )

        if not response or not response[0]:
            return []

        neighbors = response[0]
        chunk_ids = [n.id for n in neighbors]
        scores = {n.id: float(n.distance) for n in neighbors}

        hydrated = self._hydrate_from_bq(chunk_ids)

        for chunk in hydrated:
            raw_distance = scores.get(chunk.chunk_id, 1.0)
            chunk.score = 1.0 - raw_distance

        hydrated.sort(key=lambda c: c.score, reverse=True)
        logger.info("Vector search returned %d results", len(hydrated))
        return hydrated

    def _hydrate_from_bq(self, chunk_ids: list[str]) -> list[RetrievedChunk]:
        if not chunk_ids:
            return []

        placeholders = ", ".join(f"'{cid}'" for cid in chunk_ids)
        sql = f"""
        SELECT chunk_id, doc_id, title, content, source_type, metadata
        FROM `{self._bq_table}`
        WHERE chunk_id IN ({placeholders})
        """
        results = self._bq_client.query(sql).result()

        chunks: list[RetrievedChunk] = []
        for row in results:
            chunks.append(
                RetrievedChunk(
                    chunk_id=row.chunk_id,
                    doc_id=row.doc_id,
                    title=row.title,
                    content=row.content,
                    source_type=row.source_type,
                    metadata=row.metadata if row.metadata else {},
                )
            )
        return chunks
