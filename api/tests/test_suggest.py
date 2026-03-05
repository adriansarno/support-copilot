"""Tests for the /suggest-reply endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from api.tests.conftest import MOCK_INFERENCE_SUGGEST_RESPONSE


def test_suggest_reply(client, auth_headers):
    with patch(
        "api.app.services.chat_service.call_inference_suggest",
        new_callable=AsyncMock,
        return_value=MOCK_INFERENCE_SUGGEST_RESPONSE,
    ):
        resp = client.post(
            "/suggest-reply/",
            json={
                "ticket_subject": "Order not received",
                "ticket_body": "I ordered 5 days ago and haven't received my package.",
                "agent_notes": "Check shipping status",
            },
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert len(data["reply"]) > 0


def test_suggest_reply_minimal(client, auth_headers):
    with patch(
        "api.app.services.chat_service.call_inference_suggest",
        new_callable=AsyncMock,
        return_value=MOCK_INFERENCE_SUGGEST_RESPONSE,
    ):
        resp = client.post(
            "/suggest-reply/",
            json={
                "ticket_subject": "Billing question",
                "ticket_body": "Why was I charged twice?",
            },
            headers=auth_headers,
        )
    assert resp.status_code == 200
