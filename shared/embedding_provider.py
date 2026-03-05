"""Unified embedding interface: Vertex AI text-embedding or OpenAI embeddings."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from google import genai
from google.genai import types as genai_types
from openai import AsyncOpenAI


@dataclass
class EmbeddingResult:
    embeddings: list[list[float]]
    token_count: int = 0


class EmbeddingProvider:
    VERTEX_BATCH_LIMIT = 250
    OPENAI_BATCH_LIMIT = 2048

    def __init__(
        self,
        provider: str,
        model: str,
        *,
        dimension: int = 256,
        api_key: str = "",
    ):
        self.provider = provider
        self.model = model
        self.dimension = dimension

        if provider == "vertex":
            self._gemini = genai.Client()
        elif provider == "openai":
            self._openai = AsyncOpenAI(api_key=api_key)
        else:
            raise ValueError(f"Unknown embedding provider: {provider}")

    async def embed(self, texts: list[str]) -> EmbeddingResult:
        if self.provider == "vertex":
            return await self._embed_vertex(texts)
        return await self._embed_openai(texts)

    async def embed_single(self, text: str) -> list[float]:
        result = await self.embed([text])
        return result.embeddings[0]

    async def _embed_vertex(self, texts: list[str]) -> EmbeddingResult:
        all_embeddings: list[list[float]] = []
        total_tokens = 0

        for i in range(0, len(texts), self.VERTEX_BATCH_LIMIT):
            batch = texts[i : i + self.VERTEX_BATCH_LIMIT]
            result = await self._embed_vertex_batch_with_retry(batch)
            all_embeddings.extend(result.embeddings)
            total_tokens += result.token_count

        return EmbeddingResult(embeddings=all_embeddings, token_count=total_tokens)

    async def _embed_vertex_batch_with_retry(
        self, batch: list[str], max_retries: int = 5
    ) -> EmbeddingResult:
        for attempt in range(max_retries):
            try:
                response = await self._gemini.aio.models.embed_content(
                    model=self.model,
                    contents=batch,
                    config=genai_types.EmbedContentConfig(
                        output_dimensionality=self.dimension
                    ),
                )
                embeddings = [e.values for e in response.embeddings]
                return EmbeddingResult(embeddings=embeddings)
            except Exception:
                if attempt == max_retries - 1:
                    raise
                wait = 2**attempt
                await asyncio.sleep(wait)

        raise RuntimeError("Unreachable")

    async def _embed_openai(self, texts: list[str]) -> EmbeddingResult:
        all_embeddings: list[list[float]] = []
        total_tokens = 0

        for i in range(0, len(texts), self.OPENAI_BATCH_LIMIT):
            batch = texts[i : i + self.OPENAI_BATCH_LIMIT]
            resp = await self._openai.embeddings.create(
                model=self.model,
                input=batch,
                dimensions=self.dimension,
            )
            all_embeddings.extend([d.embedding for d in resp.data])
            total_tokens += resp.usage.total_tokens if resp.usage else 0

        return EmbeddingResult(embeddings=all_embeddings, token_count=total_tokens)
