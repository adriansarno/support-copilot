"""Unified LLM interface that routes to OpenAI, Gemini, or DeepSeek."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from google import genai
from google.genai import types as genai_types
from openai import AsyncOpenAI


@dataclass
class GenerationResult:
    text: str
    usage: dict[str, int] = field(default_factory=dict)
    raw: Any = None


class LLMProvider:
    """Swap between OpenAI-compatible APIs and Google Gemini via config."""

    DEEPSEEK_BASE_URL = "https://api.deepseek.com"

    def __init__(self, provider: str, model: str, *, api_key: str = ""):
        self.provider = provider
        self.model = model
        self._api_key = api_key

        if provider == "gemini":
            self._gemini = genai.Client()
        elif provider in ("openai", "deepseek"):
            base_url = self.DEEPSEEK_BASE_URL if provider == "deepseek" else None
            self._openai = AsyncOpenAI(api_key=api_key, base_url=base_url)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    # ------------------------------------------------------------------
    # Synchronous generate (Gemini) / async generate (OpenAI/DeepSeek)
    # ------------------------------------------------------------------

    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        response_format: dict | None = None,
    ) -> GenerationResult:
        if self.provider == "gemini":
            return await self._generate_gemini(
                messages, temperature=temperature, max_tokens=max_tokens
            )
        return await self._generate_openai(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        if self.provider == "gemini":
            async for chunk in self._stream_gemini(
                messages, temperature=temperature, max_tokens=max_tokens
            ):
                yield chunk
        else:
            async for chunk in self._stream_openai(
                messages, temperature=temperature, max_tokens=max_tokens
            ):
                yield chunk

    async def generate_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> dict:
        """Generate and parse a JSON response."""
        if self.provider == "gemini":
            result = await self._generate_gemini(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_mime="application/json",
            )
        else:
            result = await self._generate_openai(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        return json.loads(result.text)

    # ------------------------------------------------------------------
    # Gemini backend
    # ------------------------------------------------------------------

    async def _generate_gemini(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
        response_mime: str | None = None,
    ) -> GenerationResult:
        system, contents = self._split_gemini_messages(messages)
        config = genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system,
        )
        if response_mime:
            config.response_mime_type = response_mime

        response = await self._gemini.aio.models.generate_content(
            model=self.model, contents=contents, config=config
        )
        return GenerationResult(
            text=response.text or "",
            usage={
                "prompt_tokens": getattr(
                    response.usage_metadata, "prompt_token_count", 0
                ),
                "completion_tokens": getattr(
                    response.usage_metadata, "candidates_token_count", 0
                ),
            },
            raw=response,
        )

    async def _stream_gemini(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        system, contents = self._split_gemini_messages(messages)
        config = genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system,
        )
        async for chunk in self._gemini.aio.models.generate_content_stream(
            model=self.model, contents=contents, config=config
        ):
            if chunk.text:
                yield chunk.text

    @staticmethod
    def _split_gemini_messages(
        messages: list[dict[str, str]],
    ) -> tuple[str | None, list[genai_types.Content]]:
        system = None
        contents: list[genai_types.Content] = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                role = "model" if m["role"] == "assistant" else "user"
                contents.append(
                    genai_types.Content(
                        role=role,
                        parts=[genai_types.Part(text=m["content"])],
                    )
                )
        return system, contents

    # ------------------------------------------------------------------
    # OpenAI / DeepSeek backend
    # ------------------------------------------------------------------

    async def _generate_openai(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
        response_format: dict | None = None,
    ) -> GenerationResult:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        resp = await self._openai.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        return GenerationResult(
            text=choice.message.content or "",
            usage={
                "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
                "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
            },
            raw=resp,
        )

    async def _stream_openai(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        stream = await self._openai.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content
