"""Upsert embeddings to a Vertex AI Vector Search index."""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

from google.cloud import aiplatform, storage

from acquisition.embedders.embed import EmbeddedChunk

logger = logging.getLogger(__name__)


class VertexVectorStore:
    """Write embeddings to Vertex Vector Search via GCS staging."""

    def __init__(
        self,
        project: str,
        region: str,
        index_id: str,
        gcs_bucket: str,
    ):
        self._project = project
        self._region = region
        self._index_id = index_id
        self._gcs_bucket = gcs_bucket
        aiplatform.init(project=project, location=region)

    def upsert(self, chunks: list[EmbeddedChunk]) -> int:
        """Stage embeddings as JSONL on GCS, then trigger index update."""
        gcs_uri = self._stage_to_gcs(chunks)

        index = aiplatform.MatchingEngineIndex(self._index_id)
        index.update_embeddings(
            contents_delta_uri=gcs_uri,
            is_complete_overwrite=False,
        )
        logger.info(
            "Triggered Vertex index update with %d vectors from %s",
            len(chunks),
            gcs_uri,
        )
        return len(chunks)

    def _stage_to_gcs(self, chunks: list[EmbeddedChunk]) -> str:
        """Write JSONL file to GCS for Vertex index ingestion."""
        client = storage.Client(project=self._project)
        bucket = client.bucket(self._gcs_bucket)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            for c in chunks:
                record = {
                    "id": c.chunk_id,
                    "embedding": c.embedding,
                    "restricts": [
                        {"namespace": "source_type", "allow": [c.source_type]},
                        {"namespace": "doc_id", "allow": [c.doc_id]},
                    ],
                }
                f.write(json.dumps(record) + "\n")
            tmp_path = f.name

        blob_name = "vertex-index-staging/embeddings.json"
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(tmp_path)
        Path(tmp_path).unlink(missing_ok=True)

        gcs_uri = f"gs://{self._gcs_bucket}/vertex-index-staging/"
        logger.info("Staged %d embeddings to %s", len(chunks), gcs_uri)
        return gcs_uri
