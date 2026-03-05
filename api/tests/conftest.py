"""Shared test fixtures for the API service."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.app.main import app

API_KEY = "test-key-123"


@pytest.fixture(autouse=True)
def _mock_settings():
    with patch("api.app.middleware.auth.get_api_settings") as mock:
        s = mock.return_value
        s.api_key = API_KEY
        s.inference_url = "http://inference:8001"
        yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": API_KEY}


MOCK_INFERENCE_CHAT_RESPONSE = {
    "answer": "Based on the documentation [Source 1], the return policy is 30 days.",
    "citations": [
        {
            "source_index": 1,
            "chunk_id": "abc_0001",
            "title": "Return Policy",
            "source_type": "pdf",
            "content_snippet": "Our return policy allows returns within 30 days...",
        }
    ],
    "grade": {
        "relevance": 0.95,
        "faithfulness": 0.9,
        "completeness": 0.85,
        "explanation": "Answer well grounded in sources.",
        "low_confidence": False,
    },
    "sources": [
        {
            "chunk_id": "abc_0001",
            "title": "Return Policy",
            "source_type": "pdf",
            "content": "Our return policy allows returns within 30 days...",
            "score": 0.92,
        }
    ],
    "prompt_metadata": {
        "prompt_name": "answer",
        "prompt_version": "v1",
        "prompt_hash": "abc123",
    },
}

MOCK_INFERENCE_SUGGEST_RESPONSE = {
    "answer": "Dear Customer, thank you for reaching out...",
    "citations": [],
    "grade": None,
    "sources": [],
    "prompt_metadata": {
        "prompt_name": "suggest_reply",
        "prompt_version": "v1",
        "prompt_hash": "def456",
    },
}
