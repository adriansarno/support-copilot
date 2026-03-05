"""Chat session management: create, retrieve, persist conversations."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

import httpx

from api.app.config import get_api_settings

logger = logging.getLogger(__name__)

_chats: dict[str, dict] = {}


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def create_chat(first_message: str) -> tuple[str, str]:
    """Create a new chat session. Returns (chat_id, message_id)."""
    chat_id = _new_id()
    message_id = _new_id()
    _chats[chat_id] = {
        "chat_id": chat_id,
        "messages": [{"role": "user", "content": first_message, "id": message_id}],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return chat_id, message_id


def add_message(chat_id: str, role: str, content: str) -> str:
    """Append a message to an existing chat. Returns message_id."""
    if chat_id not in _chats:
        raise KeyError(f"Chat {chat_id} not found")
    message_id = _new_id()
    _chats[chat_id]["messages"].append(
        {"role": role, "content": content, "id": message_id}
    )
    return message_id


def get_chat(chat_id: str) -> dict | None:
    return _chats.get(chat_id)


def list_chats() -> list[dict]:
    items = []
    for chat in _chats.values():
        first_user = next(
            (m["content"] for m in chat["messages"] if m["role"] == "user"), ""
        )
        items.append({
            "chat_id": chat["chat_id"],
            "title": first_user[:60],
            "created_at": chat["created_at"],
            "message_count": len(chat["messages"]),
        })
    return sorted(items, key=lambda x: x["created_at"], reverse=True)


def get_history(chat_id: str) -> list[dict[str, str]]:
    """Get conversation history in the format expected by the inference service."""
    chat = _chats.get(chat_id)
    if not chat:
        return []
    return [
        {"role": m["role"], "content": m["content"]}
        for m in chat["messages"]
        if m["role"] in ("user", "assistant")
    ]


async def call_inference_chat(
    question: str,
    history: list[dict],
    *,
    top_k: int = 10,
    skip_grading: bool = False,
) -> dict:
    """Call the inference service /inference/chat endpoint."""
    settings = get_api_settings()
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{settings.inference_url}/inference/chat",
            json={
                "question": question,
                "history": history,
                "top_k": top_k,
                "skip_grading": skip_grading,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def call_inference_suggest(
    ticket_subject: str,
    ticket_body: str,
    agent_notes: str = "",
    *,
    top_k: int = 8,
) -> dict:
    """Call the inference service /inference/suggest endpoint."""
    settings = get_api_settings()
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{settings.inference_url}/inference/suggest",
            json={
                "ticket_subject": ticket_subject,
                "ticket_body": ticket_body,
                "agent_notes": agent_notes,
                "top_k": top_k,
            },
        )
        resp.raise_for_status()
        return resp.json()
