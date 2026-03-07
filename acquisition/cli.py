"""Acquisition pipeline CLI: ingest → chunk → embed → store."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

import typer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from acquisition.ingestors.pdf import PDFIngestor, Document
from acquisition.ingestors.html import HTMLIngestor
from acquisition.ingestors.confluence import ConfluenceIngestor
from acquisition.ingestors.tickets import TicketIngestor
from acquisition.chunkers.recursive import RecursiveChunker
from acquisition.chunkers.semantic import SemanticChunker
from acquisition.embedders.embed import ChunkEmbedder
from acquisition.stores.bigquery import BigQueryChunkStore
from acquisition.stores.vertex_index import VertexVectorStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

app = typer.Typer(help="Support Copilot Acquisition Pipeline")


def _get_settings():
    from shared.config import get_settings
    return get_settings()


def _get_embedding_provider():
    from shared.embedding_provider import EmbeddingProvider
    s = _get_settings()
    return EmbeddingProvider(
        provider=s.embedding_provider,
        model=s.embedding_model,
        dimension=s.embedding_dimension,
        api_key=s.openai_api_key,
    )


def _ingest_from_gcs(gs_url: str) -> list[Document]:
    """Ingest from GCS gs://bucket/path."""
    from acquisition.ingestors.gcs import GCSIngestor
    ingestor = GCSIngestor()
    return ingestor.ingest(gs_url)


def _ingest_dir(source_dir: Path) -> list[Document]:
    """Auto-detect source types in directory and ingest all."""
    docs: list[Document] = []

    pdf_ingestor = PDFIngestor()
    html_ingestor = HTMLIngestor()
    confluence_ingestor = ConfluenceIngestor()
    ticket_ingestor = TicketIngestor()

    pdf_files = list(source_dir.rglob("*.pdf"))
    if pdf_files:
        logger.info("Ingesting %d PDF files", len(pdf_files))
        docs.extend(pdf_ingestor.ingest_dir(source_dir))

    html_files = list(source_dir.rglob("*.html")) + list(source_dir.rglob("*.htm"))
    if html_files:
        is_confluence = any(
            (source_dir / "index.html").exists()
            for _ in [1]
        )
        if is_confluence:
            logger.info("Detected Confluence export, ingesting %d HTML files", len(html_files))
            docs.extend(confluence_ingestor.ingest_dir(source_dir))
        else:
            logger.info("Ingesting %d HTML files", len(html_files))
            docs.extend(html_ingestor.ingest_dir(source_dir))

    ticket_files = (
        list(source_dir.rglob("*.jsonl"))
        + list(source_dir.rglob("*.csv"))
    )
    if ticket_files:
        logger.info("Ingesting %d ticket files", len(ticket_files))
        docs.extend(ticket_ingestor.ingest_dir(source_dir))

    logger.info("Total documents ingested: %d", len(docs))
    return docs


@app.command()
def run(
    source_dir: str = typer.Option(..., help="Directory or gs://bucket/path containing source documents"),
    chunk_method: str = typer.Option("recursive", help="Chunking method: recursive | semantic"),
    chunk_size: int = typer.Option(512, help="Chunk size in characters (recursive only)"),
    chunk_overlap: int = typer.Option(64, help="Chunk overlap (recursive only)"),
    embed_batch_size: int = typer.Option(100, help="Embedding batch size"),
    version: int = typer.Option(1, help="Version tag for this ingestion run"),
    skip_vertex: bool = typer.Option(False, help="Skip Vertex Vector Search upsert"),
):
    """Run full acquisition pipeline: ingest → chunk → embed → store."""
    settings = _get_settings()

    logger.info("Starting acquisition pipeline from %s", source_dir)
    if source_dir.startswith("gs://"):
        docs = _ingest_from_gcs(source_dir)
    else:
        docs = _ingest_dir(Path(source_dir))
    if not docs:
        logger.warning("No documents found in %s", source_dir)
        raise typer.Exit(1)

    embed_provider = _get_embedding_provider()

    if chunk_method == "semantic":
        def sync_embed(texts: list[str]) -> list[list[float]]:
            result = asyncio.run(embed_provider.embed(texts))
            return result.embeddings

        chunker = SemanticChunker(embed_fn=sync_embed)
    else:
        chunker = RecursiveChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    chunks = chunker.chunk_many(docs)
    logger.info("Generated %d chunks using %s method", len(chunks), chunk_method)

    embedder = ChunkEmbedder(embed_provider, batch_size=embed_batch_size)
    embedded = asyncio.run(embedder.embed(chunks))
    logger.info("Embedded %d chunks", len(embedded))

    bq_store = BigQueryChunkStore(
        project=settings.gcp_project,
        dataset=settings.bq_dataset,
        table=settings.bq_chunks_table,
    )
    bq_store.ensure_table()
    bq_store.upsert(embedded, version=version)

    if not skip_vertex and settings.vertex_index_id:
        vertex_store = VertexVectorStore(
            project=settings.gcp_project,
            region=settings.gcp_region,
            index_id=settings.vertex_index_id,
            gcs_bucket=settings.gcs_bucket,
        )
        vertex_store.upsert(embedded)

    logger.info("Acquisition pipeline complete: %d chunks stored", len(embedded))


@app.command()
def ingest_only(
    source_dir: str = typer.Option(..., help="Directory or gs://bucket/path containing source documents"),
):
    """Ingest documents without chunking/embedding (dry run)."""
    if source_dir.startswith("gs://"):
        docs = _ingest_from_gcs(source_dir)
    else:
        docs = _ingest_dir(Path(source_dir))
    for doc in docs:
        typer.echo(f"  [{doc.source_type}] {doc.title} ({len(doc.content)} chars)")


if __name__ == "__main__":
    app()
