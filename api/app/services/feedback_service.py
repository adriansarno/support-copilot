"""Feedback storage: record thumbs up/down + comments."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_feedback: list[dict] = []


def record_feedback(
    chat_id: str,
    message_id: str,
    rating: int,
    comment: str = "",
) -> str:
    """Store a feedback record. Returns feedback_id.

    In production this writes to BigQuery; for now it's in-memory.
    """
    feedback_id = uuid.uuid4().hex[:12]
    record = {
        "feedback_id": feedback_id,
        "chat_id": chat_id,
        "message_id": message_id,
        "rating": rating,
        "comment": comment,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _feedback.append(record)
    logger.info("Recorded feedback %s: rating=%d chat=%s", feedback_id, rating, chat_id)
    return feedback_id


def list_feedback(chat_id: str | None = None) -> list[dict]:
    if chat_id:
        return [f for f in _feedback if f["chat_id"] == chat_id]
    return list(_feedback)
