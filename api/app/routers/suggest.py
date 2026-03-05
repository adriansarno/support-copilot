"""Suggest-reply endpoint: generate a customer-facing draft from ticket context."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from api.app.middleware.auth import verify_api_key
from api.app.schemas.models import (
    SuggestReplyRequest,
    SuggestReplyResponse,
    CitationResponse,
    PromptMetadataResponse,
    SourceResponse,
)
from api.app.services import chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/suggest-reply", tags=["suggest"])


@router.post("/", response_model=SuggestReplyResponse)
async def suggest_reply(
    req: SuggestReplyRequest,
    _key: str = Depends(verify_api_key),
):
    result = await chat_service.call_inference_suggest(
        ticket_subject=req.ticket_subject,
        ticket_body=req.ticket_body,
        agent_notes=req.agent_notes,
        top_k=req.top_k,
    )

    prompt_meta = result.get("prompt_metadata")
    pm = PromptMetadataResponse(**prompt_meta) if prompt_meta else None

    return SuggestReplyResponse(
        reply=result.get("answer", ""),
        citations=[CitationResponse(**c) for c in result.get("citations", [])],
        sources=[SourceResponse(**s) for s in result.get("sources", [])],
        prompt_metadata=pm,
    )
