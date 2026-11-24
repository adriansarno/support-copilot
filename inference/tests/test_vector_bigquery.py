"""BigQueryVectorRetriever with a fake BigQuery client (no Google access needed)."""

import asyncio
from types import SimpleNamespace

import pytest

from inference.retrieval import vector


class FakeClient:
    def __init__(self, rows):
        self.rows = rows
        self.sql = None
        self.job_config = None

    def query(self, sql, job_config=None):
        self.sql = sql
        self.job_config = job_config
        return SimpleNamespace(result=lambda: self.rows)


def row(chunk_id, distance, metadata=None):
    return SimpleNamespace(chunk_id=chunk_id, doc_id=f"doc-{chunk_id}", title=f"title {chunk_id}",
                           content=f"content {chunk_id}", source_type="html",
                           metadata=metadata, distance=distance)


@pytest.fixture
def retriever(monkeypatch):
    fake = FakeClient([row("a", 0.1, {"page": 1}), row("b", 0.6)])
    monkeypatch.setattr(vector.bigquery, "Client", lambda project: fake)
    r = vector.BigQueryVectorRetriever("proj", "ds", "chunks")
    return r, fake


def test_query_uses_vector_search_with_the_embedding_as_parameter(retriever):
    r, fake = retriever
    asyncio.run(r.search([0.5, 0.25], top_k=7))
    assert "VECTOR_SEARCH(" in fake.sql
    assert "TABLE `proj.ds.chunks`, 'embedding'" in fake.sql
    assert "top_k => 7" in fake.sql
    assert "distance_type => 'COSINE'" in fake.sql
    (param,) = fake.job_config.query_parameters
    assert param.name == "query_embedding"
    assert param.array_type == "FLOAT64"
    assert list(param.values) == [0.5, 0.25]


def test_rows_become_chunks_with_similarity_scores(retriever):
    r, _ = retriever
    chunks = asyncio.run(r.search([0.0], top_k=2))
    assert [c.chunk_id for c in chunks] == ["a", "b"]
    assert chunks[0].score == pytest.approx(0.9)
    assert chunks[1].score == pytest.approx(0.4)
    assert chunks[0].metadata == {"page": 1}
    assert chunks[1].metadata == {}


def test_top_k_is_written_as_an_integer(retriever):
    r, _ = retriever
    assert "top_k => 3," in r.build_sql("3")
    with pytest.raises(ValueError):
        r.build_sql("3; DROP TABLE x")
