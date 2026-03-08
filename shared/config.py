from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env" if (_PROJECT_ROOT / ".env").exists() else ".env"


class Settings(BaseSettings):
    # GCP
    gcp_project: str = ""
    gcp_region: str = "us-central1"

    # BigQuery
    bq_dataset: str = "support_copilot"
    bq_chunks_table: str = "chunks"
    bq_feedback_table: str = "feedback"
    bq_chats_table: str = "chats"

    # GCS
    gcs_bucket: str = "support-copilot-artifacts"
    gcs_raw_docs_bucket: str = ""  # e.g. support-copilot-1772757287-raw-docs; if empty, uses {gcp_project}-raw-docs

    # Vertex Vector Search
    vertex_index_id: str = ""
    vertex_index_endpoint_id: str = ""

    # LLM
    llm_provider: str = "gemini"  # openai | gemini | deepseek
    llm_model: str = "gemini-2.0-flash-001"

    # Embedding
    embedding_provider: str = "vertex"  # vertex | openai
    embedding_model: str = "text-embedding-004"
    embedding_dimension: int = 256

    # API keys
    openai_api_key: str = ""
    deepseek_api_key: str = ""

    # W&B
    wandb_api_key: str = ""
    wandb_project: str = "support-copilot"

    # Auth
    api_key: str = "change-me-in-production"
    jwt_secret: str = "change-me-in-production"

    # Prompt
    prompt_version: str = "v1"

    # Guardrails
    guardrails_enabled: bool = True
    guardrails_input_max_len: int = 2000
    guardrails_output_max_len: int = 4000

    # Inference service URL (used by API to call inference)
    inference_url: str = "http://localhost:8001"

    model_config = {"env_file": str(_ENV_FILE), "extra": "ignore"}

    @property
    def bq_chunks_full(self) -> str:
        return f"{self.gcp_project}.{self.bq_dataset}.{self.bq_chunks_table}"

    @property
    def bq_feedback_full(self) -> str:
        return f"{self.gcp_project}.{self.bq_dataset}.{self.bq_feedback_table}"

    @property
    def bq_chats_full(self) -> str:
        return f"{self.gcp_project}.{self.bq_dataset}.{self.bq_chats_table}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
