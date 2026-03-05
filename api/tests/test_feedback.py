"""Tests for the /feedback endpoint."""

from __future__ import annotations


def test_submit_feedback(client, auth_headers):
    resp = client.post(
        "/feedback/",
        json={
            "chat_id": "chat123",
            "message_id": "msg456",
            "rating": 1,
            "comment": "Very helpful answer!",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "feedback_id" in data
    assert data["status"] == "recorded"


def test_submit_negative_feedback(client, auth_headers):
    resp = client.post(
        "/feedback/",
        json={
            "chat_id": "chat123",
            "message_id": "msg789",
            "rating": -1,
            "comment": "Answer was incorrect.",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200


def test_feedback_invalid_rating(client, auth_headers):
    resp = client.post(
        "/feedback/",
        json={
            "chat_id": "chat123",
            "message_id": "msg000",
            "rating": 5,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422
