"""Chat endpoints: create, continue, list, and retrieve chats."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.app.middleware.auth import verify_api_key
from api.app.schemas.models import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    ChatListItem,
    ChatMessage,
    CitationResponse,
    GradeResponse,
    PromptMetadataResponse,
    SourceResponse,
)
from api.app.services import chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/", response_model=list[ChatListItem])
async def list_chats(_key: str = Depends(verify_api_key)):
    return chat_service.list_chats()


@router.get("/{chat_id}", response_model=ChatHistoryResponse)
async def get_chat(chat_id: str, _key: str = Depends(verify_api_key)):
    chat = chat_service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return ChatHistoryResponse(
        chat_id=chat["chat_id"],
        messages=[
            ChatMessage(role=m["role"], content=m["content"])
            for m in chat["messages"]
        ],
        created_at=chat["created_at"],
    )


@router.post("/", response_model=ChatResponse)
async def create_or_continue_chat(
    req: ChatRequest,
    _key: str = Depends(verify_api_key),
):
    if req.chat_id:
        chat = chat_service.get_chat(req.chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        user_msg_id = chat_service.add_message(req.chat_id, "user", req.message)
        chat_id = req.chat_id
    else:
        chat_id, user_msg_id = chat_service.create_chat(req.message)

    history = chat_service.get_history(chat_id)

    result = await chat_service.call_inference_chat(
        question=req.message,
        history=history[:-1],
        top_k=req.top_k,
        skip_grading=req.skip_grading,
    )

    answer = result.get("answer", "")
    assistant_msg_id = chat_service.add_message(chat_id, "assistant", answer)

    grade_data = result.get("grade")
    grade = GradeResponse(**grade_data) if grade_data else None

    prompt_meta = result.get("prompt_metadata")
    pm = PromptMetadataResponse(**prompt_meta) if prompt_meta else None

    return ChatResponse(
        chat_id=chat_id,
        message_id=assistant_msg_id,
        answer=answer,
        citations=[CitationResponse(**c) for c in result.get("citations", [])],
        grade=grade,
        sources=[SourceResponse(**s) for s in result.get("sources", [])],
        prompt_metadata=pm,
    )
