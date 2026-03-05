"""Tests for the /chat endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from api.tests.conftest import MOCK_INFERENCE_CHAT_RESPONSE


def test_create_chat(client, auth_headers):
    with patch(
        "api.app.services.chat_service.call_inference_chat",
        new_callable=AsyncMock,
        return_value=MOCK_INFERENCE_CHAT_RESPONSE,
    ):
        resp = client.post(
            "/chat/",
            json={"message": "What is your return policy?"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "chat_id" in data
    assert "message_id" in data
    assert "30 days" in data["answer"]
    assert len(data["citations"]) == 1
    assert data["grade"]["relevance"] == 0.95


def test_continue_chat(client, auth_headers):
    with patch(
        "api.app.services.chat_service.call_inference_chat",
        new_callable=AsyncMock,
        return_value=MOCK_INFERENCE_CHAT_RESPONSE,
    ):
        resp1 = client.post(
            "/chat/",
            json={"message": "What is your return policy?"},
            headers=auth_headers,
        )
        chat_id = resp1.json()["chat_id"]

        resp2 = client.post(
            "/chat/",
            json={"message": "What about exchanges?", "chat_id": chat_id},
            headers=auth_headers,
        )
    assert resp2.status_code == 200
    assert resp2.json()["chat_id"] == chat_id


def test_list_chats(client, auth_headers):
    with patch(
        "api.app.services.chat_service.call_inference_chat",
        new_callable=AsyncMock,
        return_value=MOCK_INFERENCE_CHAT_RESPONSE,
    ):
        client.post(
            "/chat/",
            json={"message": "Hello"},
            headers=auth_headers,
        )

    resp = client.get("/chat/", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1


def test_get_chat(client, auth_headers):
    with patch(
        "api.app.services.chat_service.call_inference_chat",
        new_callable=AsyncMock,
        return_value=MOCK_INFERENCE_CHAT_RESPONSE,
    ):
        resp = client.post(
            "/chat/",
            json={"message": "Hello"},
            headers=auth_headers,
        )
        chat_id = resp.json()["chat_id"]

    resp = client.get(f"/chat/{chat_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["chat_id"] == chat_id
    assert len(data["messages"]) >= 2


def test_get_chat_not_found(client, auth_headers):
    resp = client.get("/chat/nonexistent", headers=auth_headers)
    assert resp.status_code == 404


def test_unauthorized(client):
    resp = client.post("/chat/", json={"message": "hi"}, headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401
