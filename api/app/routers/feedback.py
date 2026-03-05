"""Feedback endpoint: record thumbs up/down + optional comment."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from api.app.middleware.auth import verify_api_key
from api.app.schemas.models import FeedbackRequest, FeedbackResponse
from api.app.services import feedback_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(
    req: FeedbackRequest,
    _key: str = Depends(verify_api_key),
):
    feedback_id = feedback_service.record_feedback(
        chat_id=req.chat_id,
        message_id=req.message_id,
        rating=req.rating,
        comment=req.comment,
    )
    return FeedbackResponse(feedback_id=feedback_id)
