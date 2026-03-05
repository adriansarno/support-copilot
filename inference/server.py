"""Inference service: internal API consumed by the public API service."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.config import get_settings
from shared.embedding_provider import EmbeddingProvider
from inference.retrieval.bm25 import BM25Retriever
from inference.retrieval.vector import VectorRetriever
from inference.reranker.cross_encoder import CrossEncoderReranker
from inference.generation.llm_router import get_llm_provider
from inference.generation.prompt_manager import PromptManager
from inference.grading.grader import AnswerGrader
from inference.pipeline import RAGPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pipeline: RAGPipeline | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    s = get_settings()

    embed = EmbeddingProvider(
        provider=s.embedding_provider,
        model=s.embedding_model,
        dimension=s.embedding_dimension,
        api_key=s.openai_api_key,
    )
    bm25 = BM25Retriever(s.gcp_project, s.bq_dataset, s.bq_chunks_table)
    vector = VectorRetriever(
        project=s.gcp_project,
        region=s.gcp_region,
        index_endpoint_id=s.vertex_index_endpoint_id,
        deployed_index_id="deployed_index",
        bq_dataset=s.bq_dataset,
        bq_table=s.bq_chunks_table,
    )
    reranker = CrossEncoderReranker()
    llm = get_llm_provider()
    prompts = PromptManager(prompts_dir="/app/prompts", version=s.prompt_version)
    grader = AnswerGrader(llm, prompts)

    pipeline = RAGPipeline(
        bm25_retriever=bm25,
        vector_retriever=vector,
        embedding_provider=embed,
        reranker=reranker,
        llm_provider=llm,
        prompt_manager=prompts,
        grader=grader,
    )
    logger.info("Inference pipeline initialized")
    yield


app = FastAPI(title="Support Copilot Inference", lifespan=lifespan)


class ChatRequest(BaseModel):
    question: str
    history: list[dict] = []
    top_k: int = 10
    skip_grading: bool = False


class SuggestRequest(BaseModel):
    ticket_subject: str
    ticket_body: str
    agent_notes: str = ""
    top_k: int = 8


@app.post("/inference/chat")
async def inference_chat(req: ChatRequest):
    result = await pipeline.run(
        req.question,
        history=req.history,
        top_k=req.top_k,
        skip_grading=req.skip_grading,
    )
    return result.to_dict()


@app.post("/inference/suggest")
async def inference_suggest(req: SuggestRequest):
    result = await pipeline.suggest_reply(
        ticket_subject=req.ticket_subject,
        ticket_body=req.ticket_body,
        agent_notes=req.agent_notes,
        top_k=req.top_k,
    )
    return result.to_dict()


@app.get("/health")
async def health():
    return {"status": "ok"}
