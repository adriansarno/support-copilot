"""Factory for creating the configured LLM provider."""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.config import get_settings
from shared.llm_provider import LLMProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    s = get_settings()
    api_key = ""
    if s.llm_provider == "openai":
        api_key = s.openai_api_key
    elif s.llm_provider == "deepseek":
        api_key = s.deepseek_api_key

    return LLMProvider(
        provider=s.llm_provider,
        model=s.llm_model,
        api_key=api_key,
        gcp_project=s.gcp_project,
        gcp_region=s.gcp_region,
    )
