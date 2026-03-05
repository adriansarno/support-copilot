from shared.config import Settings, get_settings

__all__ = ["Settings", "get_settings", "LLMProvider", "EmbeddingProvider"]


def __getattr__(name: str):
    if name == "LLMProvider":
        from shared.llm_provider import LLMProvider
        return LLMProvider
    if name == "EmbeddingProvider":
        from shared.embedding_provider import EmbeddingProvider
        return EmbeddingProvider
    raise AttributeError(f"module 'shared' has no attribute {name!r}")
