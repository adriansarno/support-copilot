"""Full RAG inference pipeline: retrieve → rerank → generate → cite → grade."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import AsyncIterator

from inference.retrieval.bm25 import RetrievedChunk
from inference.retrieval.hybrid import reciprocal_rank_fusion
from inference.generation.citations import CitationExtractor, Citation
from inference.grading.grader import GradeResult

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    answer: str
    citations: list[Citation]
    grade: GradeResult | None
    chunks: list[RetrievedChunk]
    prompt_metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "citations": CitationExtractor.citations_to_dict(self.citations),
            "grade": self.grade.to_dict() if self.grade else None,
            "sources": [
                {
                    "chunk_id": c.chunk_id,
                    "title": c.title,
                    "source_type": c.source_type,
                    "content": c.content[:300],
                    "score": c.score,
                }
                for c in self.chunks
            ],
            "prompt_metadata": self.prompt_metadata,
        }


class RAGPipeline:
    """Orchestrate the full RAG inference flow."""

    def __init__(
        self,
        bm25_retriever,
        vector_retriever,
        embedding_provider,
        reranker,
        llm_provider,
        prompt_manager,
        grader,
    ):
        self._bm25 = bm25_retriever
        self._vector = vector_retriever
        self._embed = embedding_provider
        self._reranker = reranker
        self._llm = llm_provider
        self._prompts = prompt_manager
        self._grader = grader
        self._cite = CitationExtractor()

    async def run(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
        *,
        top_k: int = 10,
        skip_grading: bool = False,
    ) -> PipelineResult:
        history = history or []

        bm25_results = self._bm25.search(question, top_k=top_k * 2)

        if self._vector and self._embed:
            query_emb = await self._embed.embed_single(question)
            vec_results = await self._vector.search(query_emb, top_k=top_k * 2)
            fused = reciprocal_rank_fusion(bm25_results, vec_results, k=60)
        else:
            fused = bm25_results

        reranked = self._reranker.rerank(question, fused, top_k=top_k) if self._reranker else fused[:top_k]

        system_prompt = self._prompts.render("system", company_name="Acme Corp")
        answer_prompt = self._prompts.render(
            "answer",
            chunks=[
                {"source_type": c.source_type, "title": c.title, "content": c.content}
                for c in reranked
            ],
            history=history,
            question=question,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": answer_prompt},
        ]

        result = await self._llm.generate(messages)
        answer_text, citations = self._cite.extract(result.text, reranked)

        grade = None
        if not skip_grading:
            grade = await self._grader.grade(question, answer_text, reranked)

        prompt_meta = self._prompts.get_metadata("answer")

        return PipelineResult(
            answer=answer_text,
            citations=citations,
            grade=grade,
            chunks=reranked,
            prompt_metadata=prompt_meta,
        )

    async def stream(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
        *,
        top_k: int = 10,
    ) -> AsyncIterator[str]:
        """Stream the answer tokens (no grading in streaming mode)."""
        history = history or []

        bm25_results = self._bm25.search(question, top_k=top_k * 2)

        if self._vector and self._embed:
            query_emb = await self._embed.embed_single(question)
            vec_results = await self._vector.search(query_emb, top_k=top_k * 2)
            fused = reciprocal_rank_fusion(bm25_results, vec_results, k=60)
        else:
            fused = bm25_results

        reranked = self._reranker.rerank(question, fused, top_k=top_k) if self._reranker else fused[:top_k]

        system_prompt = self._prompts.render("system", company_name="Acme Corp")
        answer_prompt = self._prompts.render(
            "answer",
            chunks=[
                {"source_type": c.source_type, "title": c.title, "content": c.content}
                for c in reranked
            ],
            history=history,
            question=question,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": answer_prompt},
        ]

        async for token in self._llm.stream(messages):
            yield token

    async def suggest_reply(
        self,
        ticket_subject: str,
        ticket_body: str,
        agent_notes: str = "",
        *,
        top_k: int = 8,
    ) -> PipelineResult:
        """Generate a suggested customer-facing reply for a ticket."""
        query = f"{ticket_subject} {ticket_body}"

        bm25_results = self._bm25.search(query, top_k=top_k * 2)

        if self._vector and self._embed:
            query_emb = await self._embed.embed_single(query)
            vec_results = await self._vector.search(query_emb, top_k=top_k * 2)
            fused = reciprocal_rank_fusion(bm25_results, vec_results, k=60)
        else:
            fused = bm25_results

        reranked = self._reranker.rerank(query, fused, top_k=top_k) if self._reranker else fused[:top_k]

        system_prompt = self._prompts.render("system", company_name="Acme Corp")
        reply_prompt = self._prompts.render(
            "suggest_reply",
            ticket_subject=ticket_subject,
            ticket_body=ticket_body,
            chunks=[
                {"source_type": c.source_type, "title": c.title, "content": c.content}
                for c in reranked
            ],
            agent_notes=agent_notes,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": reply_prompt},
        ]

        result = await self._llm.generate(messages)
        answer_text, citations = self._cite.extract(result.text, reranked)
        prompt_meta = self._prompts.get_metadata("suggest_reply")

        return PipelineResult(
            answer=answer_text,
            citations=citations,
            grade=None,
            chunks=reranked,
            prompt_metadata=prompt_meta,
        )
